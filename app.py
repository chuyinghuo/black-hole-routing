import os
import sys
from flask import Flask, redirect, url_for, send_from_directory, send_file, jsonify
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

# React build directory
REACT_BUILD_DIR = BASE_DIR / 'react-frontend' / 'build'
TEMPLATE_DIR = BASE_DIR / 'frontend' / 'templates'
STATIC_DIR = BASE_DIR / 'frontend' / 'static'

def create_app():
    # Check if React build exists, otherwise use Flask templates
    if REACT_BUILD_DIR.exists():
        app = Flask(
            __name__,
            static_folder=str(REACT_BUILD_DIR / 'static'),
            template_folder=str(REACT_BUILD_DIR)
        )
    else:
        app = Flask(
            __name__,
            static_folder=str(STATIC_DIR),
            template_folder=str(TEMPLATE_DIR)
        )
    
    # Enable CORS for development
    CORS(app, origins=[
        "http://localhost:3000",      # React dev server
        "http://127.0.0.1:3000",
        "http://localhost:5001",      # Flask server serving React app
        "http://127.0.0.1:5001"
    ])

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
    from api.auth.routes import auth_bp 
    from api.blocklist.routes import blocklist_bp
    from api.safelist.routes import safelist_bp
    from api.users.routes import users_bp
    from api.dashboard.routes import dashboard_bp
    from api.chatbot.routes import chatbot_bp

    # Register blueprints with /api prefix to avoid conflicts with React routes
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(blocklist_bp, url_prefix="/api/blocklist")
    app.register_blueprint(safelist_bp, url_prefix="/api/safelist")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return jsonify({"status": "healthy"})

    # React routing support
    @app.route("/")
    def root():
        if REACT_BUILD_DIR.exists():
            return send_file(REACT_BUILD_DIR / 'index.html')
        else:
            return redirect(url_for('dashboard.root'))

    # Serve React static files
    @app.route('/static/<path:filename>')
    def serve_react_static(filename):
        if REACT_BUILD_DIR.exists():
            return send_from_directory(REACT_BUILD_DIR / 'static', filename)
        else:
            return send_from_directory(STATIC_DIR, filename)

    # Serve images from React build directory
    @app.route('/images/<path:filename>')
    def serve_images(filename):
        if REACT_BUILD_DIR.exists():
            return send_from_directory(REACT_BUILD_DIR / 'images', filename)
        else:
            return send_from_directory(STATIC_DIR / 'images', filename)

    # Handle React Router routes (catch-all for frontend routes)
    @app.route('/<path:path>')
    def serve_react_app(path):
        # Let API routes be handled by Flask blueprints
        if path.startswith('api/') or path == 'health':
            # Flask will handle these routes through blueprints
            return jsonify({'error': 'API endpoint not found'}), 404
        
        # For all non-API routes, serve the React app
        if REACT_BUILD_DIR.exists():
            return send_file(REACT_BUILD_DIR / 'index.html')
        else:
            return redirect(url_for('dashboard.root'))

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("Dropping and creating all tables in PostgreSQL...")
        #db.drop_all()
        db.create_all()

    app.run(debug=True, port=5001)