# a_11_populate_usda_db.py (Verzija prilagođena za novu strukturu)
import pandas as pd
import os
from app import create_app
from app.models import db, FoodItem

print("--- KORAK 11: PUNJENJE BAZE PODATAKA S USDA NAMIRNICAMA ---")

# Putanja do .csv dataseta
CSV_PATH = os.path.join('data', 'USDA.csv')


def populate_food_items():
    """
    Čita 'USDA.csv' i unosi namirnice u bazu.
    """
    try:
        df = pd.read_csv(CSV_PATH)
        print(f"-> Učitano {len(df)} namirnica iz datoteke: {CSV_PATH}")
    except FileNotFoundError:
        print(f"GREŠKA: Datoteka '{CSV_PATH}' nije pronađena. Jeste li je stavili u 'data' direktorij?")
        return
    except Exception as e:
        print(f"GREŠKA pri čitanju CSV datoteke: {e}")
        return

    # Očisti podatke - izbacujemo retke gdje nedostaju ključni podaci
    required_columns = ['Description', 'Calories', 'Protein', 'TotalFat', 'Carbohydrate']
    df.dropna(subset=required_columns, inplace=True)

    # Preimenuj stupce da odgovaraju našem modelu u bazi podataka
    df.rename(columns={
        'Description': 'name',
        'Calories': 'calories',
        'Protein': 'protein',
        'TotalFat': 'fat',
        'Carbohydrate': 'carbs'
    }, inplace=True)

    # Filtriramo samo potrebne stupce nakon preimenovanja
    df_to_load = df[['name', 'calories', 'protein', 'fat', 'carbs']]
    # Uklanjamo duplikate po imenu
    df_to_load.drop_duplicates(subset=['name'], inplace=True)

    print(f"Nakon čišćenja, unosim {len(df_to_load)} jedinstvenih namirnica u bazu...")

    try:
        # Koristimo to_sql za brzi unos svih podataka odjednom
        # 'food_item' je ime tablice u bazi podataka
        df_to_load.to_sql('food_item', db.engine, if_exists='append', index=False, chunksize=1000)
        print("\n-> Baza podataka je uspješno popunjena USDA namirnicama!")
    except Exception as e:
        print(f"\nGREŠKA pri spremanju u bazu: {e}")
        print("Mogući uzrok je da podaci već postoje. Pokušajte prvo obrisati stare unose.")


if __name__ == '__main__':

    app = create_app()


    with app.app_context():
        print("Brišem stare unose iz tablice namirnica (food_item)...")
        try:
            db.session.query(FoodItem).delete()
            db.session.commit()
            print("Stari unosi obrisani.")
        except Exception as e:
            db.session.rollback()
            print(f"Greška pri brisanju starih unosa: {e}")

        print("Započinjem novo punjenje...")
        populate_food_items()
