from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
#from db.models import User
from app import db  # adjust if db is defined elsewhere

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def authenticate_user():
    data = request.get_json()

    # Validate input
    if not data or not data.get("netid") or not data.get("password"):
        return jsonify({"error": "netid and password required"}), 400

    # Find user by netid
    user = db.session.query(User).filter_by(netid=data["netid"]).first()

    # Validate user and password
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    # Respond with user info
    return jsonify({
        "authenticated": True,
        "netid": user.netid,
        "role": user.role,
        "user_id": str(user.id)
    })
