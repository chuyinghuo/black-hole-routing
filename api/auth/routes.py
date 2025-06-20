from flask import Blueprint, request, jsonify, render_template
from werkzeug.security import check_password_hash
import hashlib
import sys 
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from init_db import db
from models import User, UserRole, UserToken

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET'])
def login_page():
    return render_template('auth.html')

@auth_bp.route('/auth', methods=['POST'])
def authenticate_user():
    data = request.get_json()

    # Input validation
    if not data or not data.get("netid") or not data.get("token"):
        return jsonify({"error": "netid and token required"}), 400

    netid = data["netid"]
    raw_token = data["token"]
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()

    # Lookup user by net_id and hashed token
    user = db.session.query(User).filter_by(net_id=netid, token=hashed_token, active=True).first()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Respond with user info
    return jsonify({
        "authenticated": True,
        "netid": user.net_id,
        "role": user.role.value,  # Enum value
        "user_id": str(user.id)
    })