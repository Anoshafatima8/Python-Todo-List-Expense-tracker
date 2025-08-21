import os
import time
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()

# ---------------------------------------
# Flask config
# ---------------------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "dev-secret-change-me"  # change in production

db = SQLAlchemy(app)

# ---------------------------------------
# DB model
# ---------------------------------------
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.id} {self.title} done={self.done}>"

with app.app_context():
    db.create_all()

# ---------------------------------------
# To-Do Views (CRUD + mark as done)
# ---------------------------------------
@app.route("/", methods=["GET"])
def index():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required", "error")
        return redirect(url_for("index"))
    db.session.add(Task(title=title))
    db.session.commit()
    flash("Task added", "ok")
    return redirect(url_for("index"))

@app.route("/done/<int:task_id>", methods=["POST"])
def done(task_id):
    task = Task.query.get_or_404(task_id)
    if not task.done:
        task.done = True
        db.session.commit()
        flash("Task marked as done", "ok")
    return redirect(url_for("index"))

@app.route("/edit/<int:task_id>", methods=["POST"])
def edit(task_id):
    task = Task.query.get_or_404(task_id)
    new_title = request.form.get("title", "").strip()
    if not new_title:
        flash("Title is required", "error")
        return redirect(url_for("index"))
    task.title = new_title
    db.session.commit()
    flash("Task updated", "ok")
    return redirect(url_for("index"))

@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted", "ok")
    return redirect(url_for("index"))

# ---------------------------------------
# Weather API + Caching (/weather/<city>)
# ---------------------------------------
OWM_API_KEY = os.getenv("OWM_API_KEY")
WEATHER_TTL_SECONDS = 600  # 10 minutes

# Simple in-memory cache: { city_lower: {"ts": epoch_seconds, "data": {...}} }
WEATHER_CACHE = {}

# OPTIONAL: Redis cache (uncomment if you want Redis)
# import json
# import redis
# REDIS_URL = os.getenv("REDIS_URL")
# redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None

def fetch_weather_from_api(city: str):
    """Call OpenWeatherMap and return dict with needed fields."""
    if not OWM_API_KEY:
        return None, "Missing OWM_API_KEY (set it in .env)", 500

    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OWM_API_KEY, "units": "metric"},
            timeout=10,
        )
    except requests.RequestException as e:
        return None, f"Upstream error: {e}", 502

    if resp.status_code != 200:
        return None, resp.text, resp.status_code

    j = resp.json()
    out = {
        "city": j.get("name", city),
        "temperature_c": j.get("main", {}).get("temp"),
        "humidity": j.get("main", {}).get("humidity"),
        "condition": (j.get("weather") or [{}])[0].get("description"),
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }
    return out, None, 200

def cache_get(city: str):
    """Get from cache (in-memory). Return (data or None, cached_bool)."""
    key = city.strip().lower()
    item = WEATHER_CACHE.get(key)
    if not item:
        return None, False
    if time.time() - item["ts"] > WEATHER_TTL_SECONDS:
        WEATHER_CACHE.pop(key, None)
        return None, False
    return item["data"], True

def cache_set(city: str, data: dict):
    key = city.strip().lower()
    WEATHER_CACHE[key] = {"ts": time.time(), "data": data}

# If you want Redis instead of the dict cache, replace cache_get/cache_set with:
# def cache_get(city: str):
#     if not redis_client: return (None, False)
#     key = f"weather:{city.strip().lower()}"
#     val = redis_client.get(key)
#     if not val: return (None, False)
#     return json.loads(val), True
#
# def cache_set(city: str, data: dict):
#     if not redis_client: return
#     key = f"weather:{city.strip().lower()}"
#     redis_client.setex(key, WEATHER_TTL_SECONDS, json.dumps(data))

@app.route("/weather/<city>", methods=["GET"])
def weather(city):
    # 1) check cache
    cached_data, was_cached = cache_get(city)
    if was_cached:
        return jsonify({**cached_data, "cached": True})

    # 2) fetch fresh
    data, err, code = fetch_weather_from_api(city)
    if err:
        return jsonify({"error": err}), code

    # 3) write cache and return
    cache_set(city, data)
    return jsonify({**data, "cached": False})

# ---------------------------------------
# Run
# ---------------------------------------
if __name__ == "__main__":
    # Visit: http://127.0.0.1:5000/
    # Weather API: http://127.0.0.1:5000/weather/Karachi
    app.run(debug=True)
