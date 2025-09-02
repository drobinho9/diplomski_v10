# create_db.py
from app import app, db

print("--- Skripta za kreiranje baze podataka ---")

# app.app_context() osigurava da Flask zna gdje treba kreirati bazu
# u odnosu na 'app.py' datoteku.
with app.app_context():
    try:
        print("Pokušavam kreirati sve tablice...")
        db.create_all()
        print(">>> Uspjeh! Baza podataka i sve tablice su uspješno kreirane.")
        print(">>> Datoteka 'database.db' bi se sada trebala nalaziti u vašem projektnom direktoriju.")
    except Exception as e:
        print(f"Došlo je do greške: {e}")

print("--- Skripta je završila ---")