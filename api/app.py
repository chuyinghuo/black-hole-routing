# app.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
import os, sys

from models import db  
from blocklist.routes import blocklist_bp
from safelist.routes import safelist_bp
from users.routes import users_bp

# Temporary: Add parent to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

# Template dir setup
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / 'templates'

def create_app():
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)  

    # Register blueprints
    app.register_blueprint(blocklist_bp, url_prefix="/blocklist")
    app.register_blueprint(safelist_bp, url_prefix="/safelist")
    app.register_blueprint(users_bp, url_prefix="/users")

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
       db.drop_all()
       db.create_all()
    app.run(debug=True)
