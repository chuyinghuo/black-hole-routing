import csv
from datetime import datetime
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from models import User, Blocklist, Safelist, Historical, BlockHistory, UserToken, UserRole
from init_db import db
from app import app

base_path = os.path.dirname(__file__)

def load_users():
    with app.app_context(), open(os.path.join(base_path, "Users.csv"), newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if User.query.filter_by(user_id=row["user_id"]).first():
                continue
            db.session.add(User(
                user_id=row["user_id"],
                role=UserRole(row["role"]),
                added_at=datetime.fromisoformat(row["added_at"]),
                token=row["token"]
            ))
        db.session.commit()
        print("Loaded Users ✅")

def load_blocklist():
    with app.app_context(), open(os.path.join(base_path, "Blocklist.csv"), newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            exists = Blocklist.query.filter_by(ip_address=row["ip_address"], added_at=datetime.fromisoformat(row["added_at"])).first()
            if exists:
                continue
            db.session.add(Blocklist(
                ip_address=row["ip_address"],
                created_by=int(row["created_by"]),
                comment=row["comment"],
                added_at=datetime.fromisoformat(row["added_at"]),
                duration=row["duration"],
                blocks_count=int(row["blocks_count"]),
                expires_at=datetime.fromisoformat(row["expires_at"])
            ))
        db.session.commit()
        print("Loaded Blocklist ✅")

def load_safelist():
    with app.app_context(), open(os.path.join(base_path, "Safelist.csv"), newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if Safelist.query.filter_by(ip_address=row["ip_address"]).first():
                continue
            db.session.add(Safelist(
                ip_address=row["ip_address"],
                created_by=int(row["created_by"]),
                added_at=datetime.fromisoformat(row["added_at"]),
                comment=row["comment"]
            ))
        db.session.commit()
        print("Loaded Safelist ✅")

def load_historical():
    with app.app_context(), open(os.path.join(base_path, "Historical.csv"), newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            exists = Historical.query.filter_by(ip_address=row["ip_address"], added_at=datetime.fromisoformat(row["added_at"])).first()
            if exists:
                continue
            db.session.add(Historical(
                ip_address=row["ip_address"],
                created_by=int(row["created_by"]),
                comment=row["comment"],
                added_at=datetime.fromisoformat(row["added_at"]),
                unblocked_at=datetime.fromisoformat(row["unblocked_at"]),
                duration=row["duration"],
                blocks_count=int(row["blocks_count"])
            ))
        db.session.commit()
        print("Loaded Historical ✅")

def load_block_history():
    with app.app_context(), open(os.path.join(base_path, "BlockHistory.csv"), newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if BlockHistory.query.filter_by(id=int(row["id"])).first():
                continue
            db.session.add(BlockHistory(
                id=int(row["id"]),
                ip_address=row["ip_address"],
                created_by=int(row["created_by"]),
                comment=row["comment"],
                added_at=datetime.fromisoformat(row["added_at"]),
                unblocked_at=datetime.fromisoformat(row["unblocked_at"])
            ))
        db.session.commit()
        print("Loaded BlockHistory ✅")

def load_user_tokens():
    with app.app_context(), open(os.path.join(base_path, "UserTokens.csv"), newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if UserToken.query.filter_by(token=row["token"]).first():
                continue
            db.session.add(UserToken(
                token=row["token"],
                user_id=int(row["user_id"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                revoked=row["revoked"].lower() == "true",
                purpose=row["purpose"]
            ))
        db.session.commit()
        print("Loaded UserTokens ✅")

def load_all():
    load_users()
    load_blocklist()
    load_safelist()
    load_historical()
    load_block_history()
    load_user_tokens()

if __name__ == "__main__":
    load_all()
