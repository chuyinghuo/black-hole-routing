from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from pathlib import Path
from blocklist.routes import blocklist_bp
from safelist.routes import safelist_bp
from flask_sqlalchemy import SQLAlchemy
from models import db

# Temporary: Add parent to sys.path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

# Import DB instance
from __init_db__ import db

# Define base path for templates
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / 'templates'

def create_app():
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    CORS(app)

    # Use PostgreSQL URL from .env or fallback to SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///local.db"  # Fallback if .env not found
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


    # Initialize DB
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(blocklist_bp, url_prefix="/blocklist")
    app.register_blueprint(safelist_bp, url_prefix="/safelist")

    return app

if __name__ == "__main__":
    app = create_app()

    # Create tables if they don't exist (optional for dev)
    with app.app_context():
        db.create_all()

    app.run(debug=True)