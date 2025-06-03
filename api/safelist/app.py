# app.py
from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
#from routes import safelist_bp
from api.models import db



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Johamad220022@localhost:5432/project'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Register blueprint
app.register_blueprint(safelist_bp)

if __name__ == '__main__':
    app.run(debug=True)