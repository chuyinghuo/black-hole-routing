import os
import sys
from flask import Flask
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv

# Set up base directory and sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))  # Allow imports from project root

# Load environment variables
load_dotenv(dotenv_path=BASE_DIR / '.env')

# Import db AFTER sys.path and dotenv setup
from init_db import db

TEMPLATE_DIR = BASE_DIR / 'templates'

def create_app():
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    CORS(app)

    # PostgreSQL-only configuration
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL or not DATABASE_URL.startswith("postgresql://"):
        raise RuntimeError("Invalid or missing DATABASE_URL. Must be a PostgreSQL URI.")

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize the db with the app
    db.init_app(app)

    # Import models and blueprints after db is set
    from models import User, Safelist, Blocklist
    from api.blocklist.routes import blocklist_bp
    from api.safelist.routes import safelist_bp
    from api.users.routes import users_bp

    # Register blueprints
    app.register_blueprint(blocklist_bp, url_prefix="/blocklist")
    app.register_blueprint(safelist_bp, url_prefix="/safelist")
    app.register_blueprint(users_bp, url_prefix="/users")

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("Dropping and creating all tables in PostgreSQL...")
        db.drop_all()
        db.create_all()
    app.run(debug=True)
