from flask import Blueprint, request, jsonify, render_template
import sys 
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from init_db import db
from models import User, UserRole, UserToken
from datetime import datetime

users_bp = Blueprint('users', __name__, template_folder='templates')

@users_bp.route('/')
def add_user_form():
    return render_template('users.html')

@users_bp.route('/add-user', methods=['POST'])
def add_user():
    data = request.get_json()
    required_fields = ["net_id", "token", "role"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if db.session.query(User).filter_by(net_id=data["net_id"]).first():
        return jsonify({"error": "User with this net_id already exists"}), 409

    try:
        role = UserRole(data['role'])
    except ValueError:
        return jsonify({"error": "Invalid role"}), 400

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

@users_bp.route('/users', methods=['GET'])
def get_users():
    try:
        role_filter = request.args.get('role')
        search_term = request.args.get('search', '').strip()
        sort_field = request.args.get('sort', 'id')
        sort_order = request.args.get('order', 'asc')

        sort_options = {
            "id": User.id,
            "net_id": User.net_id,
            "role": User.role,
            "added_at": User.added_at
        }

        if sort_field not in sort_options:
            return jsonify({"error": "Invalid sort field"}), 400

        sort_column = sort_options[sort_field]
        sort_column = sort_column.desc() if sort_order == 'desc' else sort_column.asc()

        query = User.query

        if role_filter:
            try:
                role_enum = UserRole(role_filter)
                query = query.filter_by(role=role_enum)
            except ValueError:
                return jsonify({"error": "Invalid role filter"}), 400

        if search_term:
            query = query.filter(User.net_id.ilike(f"%{search_term}%"))

        users = query.order_by(sort_column).all()

        data = [{
            "id": user.id,
            "net_id": user.net_id,
            "role": user.role.value,
            "added_at": user.added_at.isoformat(),
            "token": user.token,
            "active": user.active
        } for user in users]
        return jsonify({"users": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        user.token = data["token"]

    try:
        db.session.commit()
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route('/remove-user/<int:user_id>', methods=['DELETE'])
def revoke_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.active = False
    db.session.commit()
    return jsonify({'message': f'User {user.net_id} revoked successfully'}), 200

@users_bp.route('/reinstate-user/<int:user_id>', methods=['POST'])
def reinstate_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.active:
        return jsonify({'message': 'User is already active'}), 200
    user.active = True
    db.session.commit()
    return jsonify({'message': f'User {user.net_id} reinstated successfully'}), 200