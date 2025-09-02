# app/services.py
import os
import random
import urllib.parse
import joblib
import pandas as pd
from datetime import datetime, timedelta, date
from app.models import Exercise, MealLog, MoodLog, WaterLog, WorkoutLog, User
from config import Config
from app import db
from sqlalchemy import func


def generate_workout_plan(user):
    all_exercises = Exercise.query.all()
    final_exercise_pool = []
    if user.equipment == 'gym':
        final_exercise_pool = all_exercises
    else:
        allowed_equipment = ['Body-Only', 'Body Only']
        if user.equipment == 'home_dumbbells':
            allowed_equipment.append('Dumbbells')
        for ex in all_exercises:
            if any(allowed in ex.equipment_needed for allowed in allowed_equipment):
                final_exercise_pool.append(ex)

    if not final_exercise_pool:
        return {"Greška": "Nije pronađeno dovoljno vježbi."}

    push_pool = [ex for ex in final_exercise_pool if ex.body_part_targeted in ['Chest', 'Shoulders', 'Triceps']]
    pull_pool = [ex for ex in final_exercise_pool if ex.body_part_targeted in ['Back', 'Biceps', 'Lats']]
    legs_pool = [ex for ex in final_exercise_pool if
                 ex.body_part_targeted in ['Legs', 'Calves', 'Glutes', 'Hamstrings', 'Quads']]

    def safe_sample(pool, k):
        return random.sample(pool, min(len(pool), k))

    workout_plan = {}
    if user.goal == 'muscle_gain':
        workout_plan = {
            "Ponedjeljak (Push)": safe_sample(push_pool, 5), "Utorak (Pull)": safe_sample(pull_pool, 5),
            "Srijeda": ["Odmor"], "Četvrtak (Legs)": safe_sample(legs_pool, 5),
            "Petak (Gornji dio)": safe_sample(push_pool + pull_pool, 5), "Subota": ["Odmor"], "Nedjelja": ["Odmor"]
        }
    else:
        full_body = safe_sample(push_pool, 2) + safe_sample(pull_pool, 2) + safe_sample(legs_pool, 2)
        workout_plan = {
            "Dan 1": full_body, "Dan 2": ["Odmor"], "Dan 3": full_body, "Dan 4": ["Odmor"],
            "Dan 5": full_body, "Dan 6": ["Odmor"], "Dan 7": ["Odmor"]
        }

    final_plan = {}
    for day, exercises in workout_plan.items():
        if exercises and isinstance(exercises[0], Exercise):
            exercise_list = []
            for ex in exercises:
                query = urllib.parse.quote(f"{ex.exercise_name} exercise tutorial")
                link = f"https://www.youtube.com/results?search_query={query}"
                exercise_list.append({"name": ex.exercise_name, "link": link})
            final_plan[day] = exercise_list
        else:
            final_plan[day] = exercises
    return final_plan


# --- SERVIS ZA PREPORUKE OBROKA ---
try:
    agent_gain = joblib.load(os.path.join(Config.MODELS_PATH, 'final_rl_agent_muscle_gain.joblib'))
    agent_loss = joblib.load(os.path.join(Config.MODELS_PATH, 'final_rl_agent_weight_loss.joblib'))
    agents = {'muscle_gain': agent_gain, 'weight_loss': agent_loss, 'maintenance': agent_loss}
    df_recipes = pd.read_csv(os.path.join(Config.PROCESSED_DATA_PATH, 'recipes_processed.csv'))
    df_recipes.dropna(subset=['calories', 'url'], inplace=True)
except Exception:
    agents = {}
    df_recipes = pd.DataFrame()


def get_meal_recommendations(user, day_of_week=0, calories_consumed=0, emotion_text="neutral"):
    if not agents or df_recipes.empty:
        return [{"name": "Greška", "calories": 0, "link": "#", "error": "Modeli ili recepti nisu dostupni."}]

    agent = agents.get(user.goal)
    if not agent:
        return [{"name": "Greška", "calories": 0, "link": "#", "error": "Agent za vaš cilj nije pronađen."}]

    goal_map = {'weight_loss': 0, 'maintenance': 1, 'muscle_gain': 2}
    user_goal_idx = goal_map.get(user.goal, 1)

    caloric_status = 0 if calories_consumed < 500 else 1 if calories_consumed < 1500 else 2
    current_state = (day_of_week, user_goal_idx, caloric_status, 1)

    agent.epsilon = 0.0
    abstract_action = agent.choose_action(current_state)

    if abstract_action == 0:
        candidates = df_recipes[df_recipes['calories'].between(100, 450)]
    elif abstract_action == 1:
        candidates = df_recipes[df_recipes['calories'].between(451, 700)]
    else:
        candidates = df_recipes[df_recipes['calories'] > 700]

    if candidates.empty:
        return [{"name": "Nema recepata", "calories": 0, "link": "#", "error": "Nema odgovarajućih recepata."}]

    chosen_recipes = candidates.sample(n=min(len(candidates), 3)).to_dict('records')

    recommendations = []
    for recipe in chosen_recipes:
        recommendations.append({
            "name": recipe.get('recipe_name'),
            "calories": int(recipe.get('calories')),
            "link": recipe.get('url')
        })
    return recommendations


# --- SERVIS ZA TJEDNI IZVJEŠTAJ ---
def generate_weekly_report(user_id):
    """Generira podatke za tjedni izvještaj za određenog korisnika."""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=7)

    workout_logs = WorkoutLog.query.filter(WorkoutLog.user_id == user_id, WorkoutLog.date >= start_date).all()
    meal_logs = MealLog.query.filter(MealLog.user_id == user_id, MealLog.date >= start_date).all()
    mood_logs = MoodLog.query.filter(MoodLog.user_id == user_id, MoodLog.date >= start_date).all()
    water_logs = WaterLog.query.filter(WaterLog.user_id == user_id, WaterLog.date >= start_date).all()

    workout_count = len(workout_logs)
    total_calories = sum(log.calories for log in meal_logs if log.calories)
    avg_daily_calories = round(total_calories / 7, 1) if meal_logs else 0
    total_water = sum(log.amount_ml for log in water_logs if log.amount_ml)
    avg_daily_water = round(total_water / 7, 1) if water_logs else 0

    mood_scores = {'excellent': 5, 'good': 4, 'okay': 3, 'bad': 2, 'terrible': 1}
    avg_mood_score = 3
    best_mood_day = None
    if mood_logs:
        avg_mood_score = sum(mood_scores.get(log.mood, 3) for log in mood_logs) / len(mood_logs)
        best_mood_day = max(mood_logs, key=lambda x: mood_scores.get(x.mood, 3)).date.isoformat()

    insights = []
    if workout_count >= 4:
        insights.append("🏆 Odličan trud s vježbanjem! Održavate sjajnu redovitost.")
    else:
        insights.append("👍 Dobar početak, pokušajte dodati još jedan trening ovaj tjedan za bolje rezultate.")

    if avg_daily_water >= 2000:
        insights.append("💧 Izvrsna hidratacija! Vaše tijelo vam je zahvalno.")
    else:
        insights.append("💧 Ne zaboravite piti dovoljno vode. Ciljajte na barem 2 litre dnevno.")

    report_data = {
        'workout_count': workout_count,
        'avg_daily_calories': avg_daily_calories,
        'avg_mood_score': round(avg_mood_score, 1),
        'avg_daily_water': avg_daily_water,
        'best_mood_day': best_mood_day,
        'period': f"{start_date.isoformat()} do {end_date.isoformat()}"
    }
    return report_data, insights


def get_demographic_insights(user):
    """Generira demografske uvide za korisnika (trenutno s primjerima)."""
    # U stvarnoj aplikaciji, ovdje bi bila kompleksnija logika koja koristi vanjske podatke
    insights = [{
        'type': 'demographic',
        'title': f'📊 Usporedba s vršnjacima ({user.age} godina) u HR',
        'message': 'Vaša dobna skupina u Hrvatskoj u prosjeku odradi 2-3 treninga tjedno.',
        'recommendation': 'Ako ste ispod prosjeka, pokušajte dodati kratki trening vikendom. Ako ste iznad, svaka čast!'
    }, {
        'type': 'health',
        'title': '🍎 Uvid u prehranu',
        'message': 'Podaci pokazuju da osobe s ciljem "gradnje mišića" često ne unose dovoljno proteina. Ciljajte na 1.6-2.2g po kg tjelesne težine.',
        'recommendation': 'Dodajte proteinski shake ili grčki jogurt u svoju prehranu.'
    }]
    return insights


# --- NOVA FUNKCIJA ZA DNEVNI SAŽETAK ---
def get_daily_summary(user_id):
    """Dohvaća i formatira sažetak unosa za današnji dan za određenog korisnika."""
    today = date.today()

    # Zbroji kalorije za danas
    total_calories = db.session.query(func.sum(MealLog.calories)).filter(
        MealLog.user_id == user_id,
        func.date(MealLog.date) == today
    ).scalar() or 0

    # Prebroji treninge za danas
    workout_count = WorkoutLog.query.filter(
        WorkoutLog.user_id == user_id,
        func.date(WorkoutLog.date) == today
    ).count()

    summary_text = f"\n\n---\n**📊 Današnji pregled:**\n- Ukupno uneseno: **{int(total_calories)} kcal**\n- Odrađeno treninga: **{workout_count}**"
    return summary_text