# a_06_fitness_recommender.py
import sys
import os
import random
import urllib.parse  # Uvozimo biblioteku za formatiranje URL-ova


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ''))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import db, User, Exercise, app

print("--- KORAK 6: RAZVOJ FITNESS PREPORUČITELJA (V4 s YouTube Linkovima) ---")


def generate_workout_plan(user):
    print(f"\nGeneriram plan za korisnika: {user.username}...")


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

    print(f"Pronađeno {len(final_exercise_pool)} odgovarajućih vježbi.")
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
            "Ponedjeljak (Push)": safe_sample(push_pool, 6), "Utorak (Pull)": safe_sample(pull_pool, 6),
            "Srijeda": ["Odmor"], "Četvrtak (Legs)": safe_sample(legs_pool, 6),
            "Petak (Gornji dio tijela)": safe_sample(push_pool + pull_pool, 6),
            "Subota": ["Odmor"], "Nedjelja": ["Odmor"]
        }
    else:
        full_body_workout = safe_sample(push_pool, 2) + safe_sample(pull_pool, 2) + safe_sample(legs_pool, 2)
        workout_plan = {
            "Dan 1 (Full Body)": full_body_workout, "Dan 2": ["Odmor"],
            "Dan 3 (Full Body)": full_body_workout, "Dan 4": ["Odmor"],
            "Dan 5 (Full Body)": full_body_workout, "Dan 6": ["Odmor"], "Dan 7": ["Odmor"]
        }


    final_plan = {}
    for day, exercises in workout_plan.items():
        if exercises and isinstance(exercises[0], Exercise):
            exercise_list_with_links = []
            for ex in exercises:
                # Formatiramo ime vježbe za korištenje u URL-u (npr. zamjenjujemo razmake s %20)
                query_text = urllib.parse.quote(f"{ex.exercise_name} exercise tutorial")
                youtube_link = f"https://www.youtube.com/results?search_query={query_text}"

                exercise_list_with_links.append({"name": ex.exercise_name, "link": youtube_link})
            final_plan[day] = exercise_list_with_links
        else:
            final_plan[day] = exercises
    # ====================================================================================

    return final_plan


if __name__ == '__main__':
    with app.app_context():
        test_user = User(
            username='test_user_final',
            goal='muscle_gain',
            fitness_level='Intermediate',
            equipment='gym'
        )
        generated_plan = generate_workout_plan(test_user)

        print("\n" + "=" * 50)
        print("GENERIRANI TJEDNI PLAN TRENINGA (V4 s YouTube Linkovima):")
        print("=" * 50)
        for day, exercises in generated_plan.items():
            print(f"\n{day}:")
            if exercises and isinstance(exercises[0], dict):
                for exercise in exercises:
                    print(f"  - {exercise['name']} --> YouTube Pretraga: {exercise['link']}")
            elif exercises:
                print(f"  - {exercises[0]}")
        print("=" * 50)