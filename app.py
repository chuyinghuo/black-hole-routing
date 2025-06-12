import os
import sys
from flask import Flask
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from models import Safelist
from init_db import db


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



    # Cleanup job function needs app context:
    def delete_expired_entries():
        with app.app_context():
            now = datetime.now(timezone.utc)
            expired_entries = Safelist.query.filter(Safelist.expires_at <= now).all()
            for entry in expired_entries:
                db.session.delete(entry)
            if expired_entries:
                db.session.commit()
            print(f"Deleted {len(expired_entries)} expired entries at {now}")

    # Start scheduler here:
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=delete_expired_entries, trigger="interval", hours=24)
    scheduler.start()

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

    # Import models and blueprints after db is set
    from models import User, Safelist, Blocklist
    from api.blocklist.routes import blocklist_bp
    from api.safelist.routes import safelist_bp
    from api.users.routes import users_bp
    from api.dashboard.routes import dashboard_bp



    # Register blueprints
    app.register_blueprint(blocklist_bp, url_prefix="/blocklist")
    app.register_blueprint(safelist_bp, url_prefix="/safelist")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')


    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("Dropping and creating all tables in PostgreSQL...")
        #db.drop_all()
        db.create_all()

    app.run(debug=True)
