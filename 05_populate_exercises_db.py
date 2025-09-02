# 05_populate_exercises_db.py
import pandas as pd
import os
from app import create_app
from app.models import db, Exercise

print("--- KORAK 5: PUNJENJE BAZE VJEŽBAMA I LINKOVIMA IZ EXCEL DATOTEKE ---")


XLSX_PATH = os.path.join('data', 'Gym_exercise_dataset.xlsx')


def populate_exercises():
    """
    Čita 'Gym_exercise_dataset.xlsx' i unosi vježbe u bazu.
    """
    try:

        df = pd.read_excel(XLSX_PATH)
        print(f"-> Učitano {len(df)} vježbi iz datoteke: {XLSX_PATH}")
    except FileNotFoundError:
        print(f"GREŠKA: Datoteka '{XLSX_PATH}' nije pronađena. Jeste li je stavili u 'data' direktorij?")
        return
    except Exception as e:
        print(f"GREŠKA pri čitanju Excel datoteke: {e}")
        return

    df.dropna(subset=['Exercise_Name', 'muscle_gp', 'Equipment', 'Description_URL'], inplace=True)


    for index, row in df.iterrows():
        new_exercise = Exercise(
            exercise_name=row['Exercise_Name'],
            body_part_targeted=row['muscle_gp'],
            equipment_needed=row['Equipment'],
            difficulty='Intermediate',
            link=row['Description_URL']
        )
        db.session.add(new_exercise)

    # Spremi sve promjene u bazu
    try:
        db.session.commit()
        print(f"\n-> Baza podataka je uspješno popunjena s {len(df)} vježbi!")
    except Exception as e:
        db.session.rollback()
        print(f"\nGREŠKA pri spremanju u bazu: {e}")


if __name__ == '__main__':

    app = create_app()


    with app.app_context():
        print("Brišem stare unose iz tablice vježbi...")
        db.session.query(Exercise).delete()
        db.session.commit()
        print("Započinjem novo punjenje...")
        populate_exercises()
