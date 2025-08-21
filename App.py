from flask import Flask, render_template, request, redirect, url_for
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# Get API key from .env
API_KEY = os.getenv("OWM_API_KEY")

# Simple in-memory task list
tasks = []

@app.route("/", methods=["GET", "POST"])
def index():
    global tasks

    if request.method == "POST":
        new_task = request.form.get("task")
        if new_task:
            tasks.append(new_task)
        return redirect(url_for("index"))

    return render_template("index.html", tasks=tasks)

@app.route("/delete/<int:task_id>")
def delete_task(task_id):
    global tasks
    if 0 <= task_id < len(tasks):
        tasks.pop(task_id)
    return redirect(url_for("index"))

@app.route("/weather", methods=["GET", "POST"])
def weather():
    city = None
    weather = None
    error = None

    if request.method == "POST":
        city = request.form.get("city")

        if city and API_KEY:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                weather = {
                    "city": city,
                    "temperature": data["main"]["temp"],
                    "description": data["weather"][0]["description"].capitalize(),
                    "icon": data["weather"][0]["icon"]
                }
            else:
                error = "❌ City not found. Please try again."
        else:
            error = "⚠️ Please enter a city name."

    return render_template("weather.html", weather=weather, city=city, error=error)

if __name__ == "__main__":
    app.run(debug=True)
