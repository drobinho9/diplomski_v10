# app/routes.py
import re
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db, groq_client
from app.models import User, WorkoutLog, MealLog, FoodItem, Exercise
from app.services import (generate_workout_plan, get_meal_recommendations,
                          generate_weekly_report, get_demographic_insights, get_daily_summary)
from thefuzz import process

main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == "POST":
        existing_email = User.query.filter_by(email=request.form.get('email')).first()
        if existing_email:
            flash('Ta email adresa se već koristi. Molimo prijavite se ili koristite drugu.', 'danger')
            return redirect(url_for('main.register'))
        existing_username = User.query.filter_by(username=request.form.get('username')).first()
        if existing_username:
            flash('To korisničko ime je zauzeto. Molimo odaberite drugo.', 'danger')
            return redirect(url_for('main.register'))
        try:
            user = User(
                username=request.form["username"], email=request.form["email"], age=int(request.form["age"]),
                gender=request.form["gender"], height=float(request.form["height"]),
                weight=float(request.form["weight"]),
                goal=request.form["goal"], fitness_level=request.form["fitness_level"],
                equipment=request.form["equipment"]
            )
            user.set_password(request.form["password"])
            db.session.add(user)
            db.session.commit()
            flash("Račun uspješno kreiran! Molimo prijavite se.", "success")
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Došlo je do neočekivane greške pri registraciji: {e}", "danger")
            return redirect(url_for('main.register'))
    return render_template("register.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and user.check_password(request.form["password"]):
            login_user(user, remember=True)
            return redirect(url_for('main.dashboard'))
        else:
            flash("Neispravan email ili lozinka.", "danger")
    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    fitness_plan = session.pop('fitness_plan', None)
    meal_recs = session.pop('meal_recs', None)
    workout_logs = WorkoutLog.query.filter_by(user_id=current_user.id).order_by(WorkoutLog.date.desc()).limit(3).all()
    meal_logs = MealLog.query.filter_by(user_id=current_user.id).order_by(MealLog.date.desc()).limit(3).all()
    return render_template("dashboard.html", user=current_user,
                           fitness_plan=fitness_plan, meal_recommendations=meal_recs,
                           workout_logs=workout_logs, meal_logs=meal_logs)


@main_bp.route("/generate_plan", methods=["POST"])
@login_required
def generate_plan():
    plan = generate_workout_plan(current_user)
    session['fitness_plan'] = plan
    flash("Novi plan treninga je generiran!", "success")
    return redirect(url_for('main.dashboard'))


@main_bp.route("/get_meals", methods=["POST"])
@login_required
def get_meals():
    try:
        calories = float(request.form.get('calories_so_far', 0))
    except (ValueError, TypeError):
        calories = 0
    recs = get_meal_recommendations(current_user, calories_consumed=calories)
    session['meal_recs'] = recs
    flash("Nove preporuke obroka su generirane!", "success")
    return redirect(url_for('main.dashboard'))


def find_best_match(query, choices):
    """Pronađi najbolji pogodak koristeći fuzzy matching."""
    if not choices: return None
    best_match = process.extractOne(query, choices)
    # Vraćamo podudaranje samo ako je sličnost vrlo visoka (npr. > 85)
    if best_match and best_match[1] > 85:
        return best_match[0]
    return None


def execute_ai_action(action_data):
    action_name = action_data.get("action")
    params = action_data.get("parameters", {})
    response_message = ""

    if action_name == "log_workout":
        try:
            exercise_query = params.get("exercise_name")
            if not exercise_query: return "❌ Niste naveli ime vježbe."

            # Logika za pretragu vježbi
            all_exercise_names = [ex.exercise_name for ex in Exercise.query.all()]
            best_match = find_best_match(exercise_query, all_exercise_names)

            if not best_match:
                return f"❌ Vježba '{exercise_query}' nije pronađena. Molimo pokušajte s drugim nazivom."

            workout = WorkoutLog(
                user_id=current_user.id,
                exercise=best_match,
                sets=int(params.get("sets")),
                reps=int(params.get("reps")),
                weight=float(params.get("weight")) if params.get("weight") else None
            )
            db.session.add(workout)
            db.session.commit()
            response_message = f"✅ Trening '{best_match}' je uspješno zabilježen!"
        except Exception as e:
            db.session.rollback()
            return f"❌ Greška pri bilježenju treninga: {e}"

    elif action_name == "log_meal":
        try:
            food_query = params.get("food_name")
            if not food_query: return "❌ Niste naveli ime namirnice."

            # Pretpostavljamo da je 'quantity' broj komada ili porcija ako jedinica nije navedena
            quantity = int(params.get("quantity", 1))

            # Logika za pretragu hrane
            all_food_names = [item.name for item in FoodItem.query.all()]
            best_match = find_best_match(food_query, all_food_names)

            if not best_match:
                return f"❌ Namirnica '{food_query}' nije pronađena. Molimo pokušajte s drugim nazivom."

            food_item = FoodItem.query.filter(FoodItem.name == best_match).first()
            if not food_item: return f"Greška: Namirnica '{best_match}' ne postoji u bazi."

            # Ovdje se može dodati naprednija logika za kalorije ako AI vrati i jedinicu (npr. "g")
            total_calories = food_item.calories * quantity
            meal = MealLog(user_id=current_user.id, food=food_item.name, quantity=quantity, calories=total_calories)
            db.session.add(meal)
            db.session.commit()
            response_message = f"✅ Obrok '{quantity}x {food_item.name}' ({int(total_calories)} kcal) je uspješno zabilježen!"
        except Exception as e:
            db.session.rollback()
            return f"❌ Greška pri bilježenju obroka: {e}"

    elif action_name == "recommend_workout":
        plan = generate_workout_plan(current_user)
        if "Greška" in plan:
            return "Trenutno ne mogu generirati plan vježbanja. Provjerite jesu li vježbe unesene u sustav."
        response_message = "Evo prijedloga treninga za tebe na temelju tvojih ciljeva:\n"
        for day, exercises in plan.items():
            response_message += f"\n**{day}:**\n"
            if isinstance(exercises[0], dict):
                for ex in exercises:
                    response_message += f"- {ex['name']}\n"
            else:
                response_message += f"- {exercises[0]}\n"
        response_message += "\nJavi mi ako želiš da zabilježimo neku od ovih vježbi kad je odradiš!"

    elif action_name == "recommend_meal":
        recommendations = get_meal_recommendations(current_user)
        if "Greška" in recommendations[0]:
            return f"Trenutno ne mogu generirati preporuke za obroke. Razlog: {recommendations[0].get('error', 'Nepoznata greška.')}"
        response_message = "Naravno, evo nekoliko ideja za obrok:\n"
        for meal in recommendations:
            if "name" in meal and "calories" in meal:
                response_message += f"- **{meal['name']}** ({meal['calories']} kcal)\n"
        response_message += "\nKoju od ovih opcija želiš da zabilježim?"

    if "zabilježen" in response_message:
        daily_summary = get_daily_summary(current_user.id)
        return response_message + daily_summary

    return response_message or "Nepoznata akcija."


@main_bp.route("/smart_input", methods=["GET", "POST"])
@login_required
def smart_input():
    # Uklonili smo slanje cijele baze u prompt!
    system_prompt = {
        "role": "system",
        "content": f"""Ti si NutriFit AI, precizan fitness asistent. Tvoj zadatak je pomoći korisniku zabilježiti obroke i vježbe.
        Informacije o korisniku: {current_user.username}, Cilj: {current_user.goal}.

        TVOJA PRAVILA:
        1. Iz korisnikove poruke izvuci IME HRANE ili VJEŽBE i povezane detalje (količina, serije, ponavljanja, težina).
        2. Ako detalji nedostaju, postavi pitanje da ih dobiješ. (Npr. za "jeo sam piletinu", pitaj "Koliko?").
        3. Nemoj izmišljati hranu ili vježbe. Samo izvuci što je korisnik rekao. Backend će pronaći točan naziv u bazi.
        4. Kada imaš sve podatke, u odgovoru uključi JSON unutar `<execute>` taga.

        PRIMJER (Hrana):
        Korisnik: jeo sam 200g piletine
        Tvoj odgovor: U redu, bilježim 200g piletine.<execute>{{"action": "log_meal", "parameters": {{"food_name": "piletina", "quantity": 200, "unit": "g"}}}}</execute>

        PRIMJER (Vježba):
        Korisnik: bench press 3 serije 10 ponavljanja 80kg
        Tvoj odgovor: Super, bilježim!<execute>{{"action": "log_workout", "parameters": {{"exercise_name": "bench press", "sets": 3, "reps": 10, "weight": 80}}}}</execute>
        """
    }

    if "chat_history" not in session:
        session["chat_history"] = []

    if request.method == "POST":
        user_msg = request.form.get("description", "").strip()
        if not user_msg:
            flash("Poruka ne može biti prazna.", "warning")
            return redirect(url_for('main.smart_input'))

        session["chat_history"].append({"role": "user", "content": user_msg})

        if groq_client:
            try:
                messages_to_send = [system_prompt] + session["chat_history"]

                resp = groq_client.chat.completions.create(
                    messages=messages_to_send,
                    model="llama-3.1-8b-instant",
                    temperature=0.2,
                    max_tokens=512,
                    top_p=0.9
                )
                ai_response_text = resp.choices[0].message.content.strip()

                action_data = None
                conversational_reply = ai_response_text
                match = re.search(r"<execute>(.*?)</execute>", ai_response_text, re.DOTALL)
                if match:
                    json_string = match.group(1)
                    try:
                        action_data = json.loads(json_string)
                        conversational_reply = ai_response_text.replace(match.group(0), "").strip()
                    except json.JSONDecodeError:
                        print(f"AI je generirao neispravan JSON: {json_string}")

                if conversational_reply:
                    session["chat_history"].append({"role": "assistant", "content": conversational_reply})

                if action_data:
                    action_result_msg = execute_ai_action(action_data)
                    session["chat_history"].append({"role": "assistant", "content": action_result_msg})

            except Exception as e:
                print(f"Greška pri pozivu Groq API-ja: {e}")
                session["chat_history"].append({"role": "assistant", "content": "Trenutno imam tehničkih poteškoća."})
        else:
            session["chat_history"].append({"role": "assistant", "content": "AI servis trenutno nije dostupan."})

        if len(session["chat_history"]) > 10:
            session["chat_history"] = session["chat_history"][-10:]

        session.modified = True
        return redirect(url_for('main.smart_input'))

    return render_template("smart_input.html", chat_history=session.get("chat_history", []))


@main_bp.route("/clear_smart_chat", methods=["POST"])
@login_required
def clear_smart_chat():
    session.pop('chat_history', None)
    flash("Razgovor je poništen. Možete započeti novi.", "info")
    return redirect(url_for('main.smart_input'))


@main_bp.route("/reports/weekly")
@login_required
def weekly_report():
    report_data, insights = generate_weekly_report(current_user.id)
    return render_template("weekly_report.html",
                           report=report_data,
                           insights=insights,
                           user=current_user)


@main_bp.route("/insights/demographics")
@login_required
def demographic_insights():
    insights = get_demographic_insights(current_user)
    return render_template("demographic_insights.html",
                           insights=insights,
                           user=current_user)


@main_bp.route("/log_workout", methods=["POST"])
@login_required
def log_workout():
    try:
        workout = WorkoutLog(
            user_id=current_user.id,
            exercise=request.form.get('exercise'),
            sets=int(request.form.get('sets', 0)),
            reps=int(request.form.get('reps', 0)),
            weight=float(request.form.get('weight')) if request.form.get('weight') else None,
            feeling=request.form.get('feeling', 'good')
        )
        db.session.add(workout)
        db.session.commit()
        flash('✅ Trening je uspješno zabilježen!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Greška pri bilježenju treninga: {e}', 'danger')
    return redirect(url_for('main.dashboard'))


@main_bp.route("/log_meal", methods=["POST"])
@login_required
def log_meal():
    try:
        meal = MealLog(
            user_id=current_user.id,
            food=request.form.get('food'),
            quantity=int(request.form.get('quantity', 1)),
            calories=float(request.form.get('calories', 0))
        )
        db.session.add(meal)
        db.session.commit()
        flash('✅ Obrok je uspješno zabilježen!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Greška pri bilježenju obroka: {e}', 'danger')
    return redirect(url_for('main.dashboard'))