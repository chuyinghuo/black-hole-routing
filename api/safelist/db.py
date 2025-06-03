from routes import db, app  # Make sure you import both

with app.app_context():
    db.drop_all()
    db.create_all()
    exit()