import sys
import os

# Add project root to sys.path so you can import app and db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from init_db import db
from models import *  # Ensures all models are registered with SQLAlchemy

# Create the Flask app
app = create_app()

with app.app_context():
    #db.drop_all
    print("Creating database tables...")
    db.create_all()
    print("Tables created")