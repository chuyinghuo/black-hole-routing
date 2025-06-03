from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from backend.models import Admin, Editor, Viewer #need to check models.py
from app import db 
users_bp = Blueprint('users', __name__)

# ════════════════════════════════════════════════
#                    CREATE
# ════════════════════════════════════════════════
@users_bp.route('/add-admin', methods=['POST'])
def add_admin():
    data = request.get_json()
    required_fields = ["net_id", "password", "time_added", "auth_key"] 
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required admin fields"}), 400

    if db.session.query(Admin).filter_by(net_id=data["net_id"]).first():
        return jsonify({"error": "Admin with this net id already exists"}), 409

    new_admin = Admin(
        net_id=data["net_id"],
        password=generate_password_hash(data["password"]),
        time_added=data["time_added"],
        auth_key=data["auth_key"]
    )
    db.session.add(new_admin)
    db.session.commit()

    return jsonify({"message": "Admin added", "admin_id": new_admin.admin_id}), 201


@users_bp.route('/add-editor', methods=['POST'])
def add_editor():
    data = request.get_json()
    required_fields = ["net_id", "password", "time_added", "auth_key"] 
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required editor fields"}), 400

    if db.session.query(Editor).filter_by(net_id=data["net_id"]).first():
        return jsonify({"error": "Admin with this net id already exists"}), 409

    new_editor = Editor(
        net_id=data["net_id"],
        password=generate_password_hash(data["password"]),
        time_added=data["time_added"],
        auth_key=data["auth_key"]
    )
    db.session.add(new_editor)
    db.session.commit()

    return jsonify({"message": "Editor added", "mentee_id": new_editor.editor_id}), 201


@users_bp.route('/add-viewer', methods=['POST'])
def add_viewer():
    data = request.get_json()
    required_fields = ["net_id", "password", "time_added", "auth_key"] 
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required viewer fields"}), 400

    if db.session.query(Viewer).filter_by(net_id=data["net_id"]).first():
        return jsonify({"error": "Viewer with this net id already exists"}), 409

    new_viewer = Viewer(
        net_id=data["net_id"],
        password=generate_password_hash(data["password"]),
        time_added=data["time_added"],
        auth_key=data["auth_key"]
    )
    db.session.add(new_viewer)
    db.session.commit()

    return jsonify({"message": "Viewer added", "viewer_id": new_viewer.viewer_id}), 201

# ════════════════════════════════════════════════
#                     READ
# ════════════════════════════════════════════════

@users_bp.route("/admins", methods=["GET"])
def get_admins():
    admins = db.session.query(Admin).all()
    data = [{
        "admin_id": admin.admin_id,
        "net_id": admin.net_id,
        "time_added": admin.time_added,
        "auth_key": admin.auth_key
    } for admin in admins]
    return jsonify({"admins": data}), 200


@users_bp.route("/editors", methods=["GET"])
def get_editors():
    editors = db.session.query(Editor).all()
    data = [{
        "editor_id": editor.editor_id,
        "net_id": editor.net_id,
        "time_added": editor.time_added,
        "auth_key": editor.auth_key
    } for editor in editors]
    return jsonify({"editors": data}), 200


@users_bp.route("/viewers", methods=["GET"])
def get_viewers():
    viewers = db.session.query(Viewer).all()
    data = [{
        "viewer_id": viewer.viewer_id,
        "net_id": viewer.net_id,
        "time_added": viewer.time_added,
        "auth_key": viewer.auth_key
    } for viewer in viewers]
    return jsonify({"viewers": data}), 200
 
# ════════════════════════════════════════════════
#                    UPDATE
# ════════════════════════════════════════════════
@users_bp.route("/edit/admin/<int:admin_id>", methods=["PUT"])
def update_admin(admin_id):
    admin = db.session.query(Admin).filter_by(admin_id=admin_id).first()
    if not admin:
        return jsonify({"error": "Admin not found"}), 404

    data = request.get_json()
    updatable_fields = {
        "net_id": str,
        "password": str,
        "auth_key": str
    }

    for field, cast in updatable_fields.items():
        if field in data:
            try:
                setattr(admin, field, cast(data[field]))
            except ValueError:
                return jsonify({"error": f"Invalid value for {field}"}), 400

    try:
        db.session.commit()
        return jsonify({"message": "Admin updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/edit/editor/<int:editor_id>", methods=["PUT"])
def update_editor(editor_id):
    editor = db.session.query(Editor).filter_by(editor_id=editor_id).first()
    if not editor:
        return jsonify({"error": "Editor not found"}), 404

    data = request.get_json()
    updatable_fields = {
        "net_id": str,
        "password": str,
        "auth_key": str
    }

    for field, cast in updatable_fields.items():
        if field in data:
            try:
                setattr(editor, field, cast(data[field]))
            except ValueError:
                return jsonify({"error": f"Invalid value for {field}"}), 400

    try:
        db.session.commit()
        return jsonify({"message": "Editor updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@users_bp.route("/edit/viewer/<int:viewer_id>", methods=["PUT"])
def update_viewer(viewer_id):
    viewer = db.session.query(Viewer).filter_by(viewer_id=viewer_id).first()
    if not viewer:
        return jsonify({"error": "Viewer not found"}), 404

    data = request.get_json()
    updatable_fields = {
        "net_id": str,
        "user_name": str,
        "first_name": str,
        "last_name": str
    }

    for field, cast in updatable_fields.items():
        if field in data:
            try:
                setattr(viewer, field, cast(data[field]))
            except ValueError:
                return jsonify({"error": f"Invalid value for {field}"}), 400

    try:
        db.session.commit()
        return jsonify({"message": "Viewer updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ════════════════════════════════════════════════
#                    DELETE
# ════════════════════════════════════════════════
# ════════════════════════════════════════════════
#                    DELETE
# ════════════════════════════════════════════════

@users_bp.route('/remove-admin/<int:admin_id>', methods=['DELETE'])
def delete_admin(admin_id):
    admin = db.session.query(Admin).filter_by(admin_id=admin_id).first()
    if not admin:
        return jsonify({"error": "Admin not found"}), 404

    try:
        db.session.delete(admin)
        db.session.commit()
        return jsonify({"message": "Admin deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@users_bp.route('/remove-editor/<int:editor_id>', methods=['DELETE'])
def delete_editor(editor_id):
    editor = db.session.query(Editor).filter_by(editor_id=editor_id).first()
    if not editor:
        return jsonify({"error": "Editor not found"}), 404

    try:
        db.session.delete(editor)
        db.session.commit()
        return jsonify({"message": "Editor deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@users_bp.route('/remove-viewer/<int:viewer_id>', methods=['DELETE'])
def delete_viewer(viewer_id):
    viewer = db.session.query(Viewer).filter_by(viewer_id=viewer_id).first()
    if not viewer:
        return jsonify({"error": "Viewer not found"}), 404

    try:
        db.session.delete(viewer)
        db.session.commit()
        return jsonify({"message": "Viewer deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500