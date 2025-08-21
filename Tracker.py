import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Secret key from .env
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "default_secret")
# Database from .env
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///expenses.db")

db = SQLAlchemy(app)

# Expense Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)

with app.app_context():
    db.create_all()

# Home page → List expenses
@app.route('/')
def index():
    expenses = Expense.query.all()
    total = sum(exp.amount for exp in expenses)
    return render_template("index.html", expenses=expenses, total=total)

# Add new expense
@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']
        category = request.form['category']
        new_expense = Expense(title=title, amount=float(amount), category=category)
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template("add_expense.html")

# Delete expense
@app.route('/delete/<int:id>')
def delete_expense(id):
    exp = Expense.query.get(id)
    db.session.delete(exp)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
