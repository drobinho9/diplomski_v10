# config.py
import os
from dotenv import load_dotenv

# Učitaj varijable iz .env datoteke
load_dotenv()

# --- ISPRAVAK: Definiramo osnovnu putanju projekta ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    """Osnovna konfiguracija aplikacije."""
    # Tajni ključ za zaštitu sesija i formi
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-super-secret-key-for-dev'

    # Postavke baze podataka
    instance_path = os.path.join(BASE_DIR, 'instance')
    os.makedirs(instance_path, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(instance_path, 'database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- ISPRAVAK: Ažurirane putanje do modela i podataka ---
    # Putanje sada pokazuju na direktorije u root-u projekta, a ne unutar 'app'
    MODELS_PATH = os.path.join(os.path.dirname(BASE_DIR), 'models')
    PROCESSED_DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), 'data', 'processed')

    # Groq API Token
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')