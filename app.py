from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from pathlib import Path
from api.blocklist.routes import blocklist_bp
from api.safelist.routes import safelist_bp
from flask_sqlalchemy import SQLAlchemy
from api.models import db




#Temporary need to delete later
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Load environment variables early
load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

# Import DB instance
from api.__init_db__ import db

# Import API blueprints
#from api.auth.routes import auth_bp
from api.blocklist.routes import blocklist_bp
from api.safelist.routes import safelist_bp
#from api.users.routes import users_bp

def create_app():
    app = Flask(__name__)
    CORS(app)


    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Johamad220022@localhost:5432/project'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize DB
    db.init_app(app)

    # Register Blueprints
    #app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(blocklist_bp, url_prefix="/blocklist")
    app.register_blueprint(safelist_bp, url_prefix="/safelist")
   # app.register_blueprint(users_bp, url_prefix="/users")

    return app

if __name__ == "__main__":
    app = create_app()
    
    # Create tables if they don't exist (optional for dev)
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)