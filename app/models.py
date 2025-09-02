# app/models.py
from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    goal = db.Column(db.String(50))
    fitness_level = db.Column(db.String(50))
    equipment = db.Column(db.String(100))
    medical_history = db.Column(db.Text)
    citizenship = db.Column(db.String(10))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(150), nullable=False)
    body_part_targeted = db.Column(db.String(100))
    equipment_needed = db.Column(db.String(100))
    difficulty = db.Column(db.String(50))
    link = db.Column(db.String(300))

class WorkoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise = db.Column(db.String(150))
    date = db.Column(db.Date, default=datetime.utcnow)
    reps = db.Column(db.Integer)
    sets = db.Column(db.Integer)
    weight = db.Column(db.Float)
    feeling = db.Column(db.String(100))

class MealLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    food = db.Column(db.String(200))
    # --- PROMJENA ---
    quantity = db.Column(db.Integer, nullable=False, default=1)
    calories = db.Column(db.Float)
    # --- KRAJ PROMJENE ---
    liked_recommendation = db.Column(db.Boolean, default=False)

class MoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    mood = db.Column(db.String(50))
    note = db.Column(db.Text)

class WaterLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    amount_ml = db.Column(db.Integer)

class ProgressReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    report_type = db.Column(db.String(50))
    generated_date = db.Column(db.Date, default=datetime.utcnow)
    data = db.Column(db.JSON)
    insights = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Float)
    protein = db.Column(db.Float)
    fat = db.Column(db.Float)
    carbs = db.Column(db.Float)