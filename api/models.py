from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import INET, INTERVAL
import ipaddress
import hashlib
from markupsafe import escape
from sqlalchemy.orm import validates
import re
 
db = SQLAlchemy()
 
class UserRole(Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
 
class User(db.Model):
    __tablename__ = 'users'
 
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    net_id = db.Column(db.String(8), unique=True, nullable=False)
    role = db.Column(SQLAlchemyEnum(UserRole, name='user_role'), nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    token = db.Column(db.Text, nullable=False, unique=True)
 
    blocklist_entries = db.relationship('Blocklist', backref='owner', lazy=True)
    safelist_entries = db.relationship('Safelist', backref='owner', lazy=True)
    historical_entries = db.relationship('Historical', backref='owner', lazy=True)
    block_history_entries = db.relationship('BlockHistory', backref='owner', lazy=True)
    user_tokens = db.relationship('UserToken', backref='owner', lazy=True)
 
    @validates('token')
    def validate_and_hash_token(self, key, token):
        # Check if token is already hashed (64 hex chars)
        if re.fullmatch(r'[a-f0-9]{64}', token):
            return token
        if not token or len(token) < 32:
            raise ValueError("Token too short")
        return hashlib.sha256(token.encode()).hexdigest()
 
class Blocklist(db.Model):
    __tablename__ = 'blocklist'
 
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    ip_address = db.Column(INET, nullable=False)
    
    # `created_by` is optional — to avoid foreign key errors if no user exists
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    comment = db.Column(db.Text, nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    duration = db.Column(INTERVAL, nullable=False)
    blocks_count = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
 
class Safelist(db.Model):
    __tablename__ = 'safelist'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    ip_address = db.Column(INET, nullable=False, unique=True)
    
    # `created_by` is optional — to avoid foreign key errors if no user exists
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    added_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    comment = db.Column(db.Text, nullable=True)
    duration = db.Column(INTERVAL, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
 
class Historical(db.Model):
    __tablename__ = 'historical'
 
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    ip_address = db.Column(INET, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    comment = db.Column(db.Text, nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    unblocked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    duration = db.Column(INTERVAL, nullable=True)
    blocks_count = db.Column(db.Integer, nullable=True)
 
class BlockHistory(db.Model):
    __tablename__ = 'block_history'
 
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(INET, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    added_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    unblocked_at = db.Column(db.DateTime(timezone=True), nullable=True)
 
class UserToken(db.Model):
    __tablename__ = 'user_tokens'
 
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.Text, unique=True, index=True, nullable=False)
    net_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
 
    @validates('token')
    def validate_and_hash_token(self, key, token):
        if not token or len(token) < 32:
            raise ValueError("Token too short")
        return hashlib.sha256(token.encode()).hexdigest()

def __repr__(self):
    return f"<IP: {self.ip}>"