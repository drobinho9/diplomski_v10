# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from groq import Groq  # <-- PROMJENA
from config import Config
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'

# Inicijalizacija Groq klijenta
groq_client = None # <-- PROMJENA
if Config.GROQ_API_KEY: # <-- PROMJENA
    groq_client = Groq(api_key=Config.GROQ_API_KEY) # <-- PROMJENA

def create_app(config_class=Config):
    """Kreira i konfigurira Flask aplikaciju."""
    app = Flask(__name__, instance_path=Config.instance_path)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        from app import models
        db.create_all()

    return app