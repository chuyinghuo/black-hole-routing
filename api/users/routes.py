from flask import Blueprint, request, jsonify, render_template
import sys 
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from init_db import db
from models import User, UserRole
from datetime import datetime

users_bp = Blueprint('users', __name__, template_folder='templates')

# ───────────── ROUTE: Render Add User Form ─────────────
@users_bp.route('/')
def add_user_form():
    return render_template('add_user.html')

# ───────────── ROUTE: Create New User ─────────────
@users_bp.route('/add-user', methods=['POST'])
def add_user():
    data = request.get_json()
    required_fields = ["net_id", "token", "role"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Check uniqueness
    if db.session.query(User).filter_by(net_id=data["net_id"]).first():
        return jsonify({"error": "User with this net_id already exists"}), 409

    # Validate role
    try:
        role = UserRole(data['role'])
    except ValueError:
        return jsonify({"error": "Invalid role"}), 400

    # Create user (token will be hashed automatically via validator)
    try:
        new_user = User(
            net_id=data["net_id"],
            token=data["token"],
            role=role,
            added_at=datetime.utcnow()
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User added", "user_id": new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ───────────── ROUTE: Read All Users ─────────────
@users_bp.route('/users', methods=['GET'])
def get_users():
    try:
        users = User.query.all()
        data = [{
            "id": user.id,
            "net_id": user.net_id,
            "role": user.role.value,
            "added_at": user.added_at.isoformat(),
            "token": user.token
        } for user in users]
        return jsonify({"users": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ───────────── ROUTE: Update User ─────────────
@users_bp.route('/edit/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if "net_id" in data:
        user.net_id = data["net_id"]
    if "role" in data:
        try:
            user.role = UserRole(data["role"])
        except ValueError:
            return jsonify({"error": "Invalid role"}), 400
    if "token" in data:
        user.token = data["token"]  # Auto-hashed in validator

    try:
        db.session.commit()
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ───────────── ROUTE: Delete User ─────────────
@users_bp.route('/remove-user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
