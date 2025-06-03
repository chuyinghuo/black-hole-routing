from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from datetime import datetime
from sqlalchemy.dialects.postgresql import CIDR, INTERVAL

from __init_db__ import db

class SafeList(db.Model):
    __tablename__ = 'safelist'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    ip_address = db.Column(db.String, unique=True, nullable=False)
    user_id = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ending_date = db.Column(db.DateTime, nullable=True)
    comment = db.Column(db.String, nullable=True)
    duration = db.Column(db.Integer)

class IpBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip = db.Column(CIDR, unique=True, nullable=False)
    num_blocks = db.Column(db.Integer, nullable=False)
    time_added = db.Column(db.DateTime, nullable=False, default=datetime)
    time_unblocked = db.Column(db.DateTime, nullable=False)
    duration = db.Column(INTERVAL, nullable=False)
    reason = db.Column(db.String(512), nullable=False)
    netid = db.Column(db.String(128), nullable=False)
    api_token = db.Column(db.String(256), nullable=False)

def __repr__(self):
        return f"<IP: {self.ip}>"
