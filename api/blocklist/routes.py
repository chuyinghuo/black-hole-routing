import ipaddress
from flask import Blueprint, render_template, request, redirect, current_app, jsonify
from datetime import datetime, timedelta, timezone
from io import StringIO
import csv
from init_db import db
from models import Blocklist, User

blocklist_bp = Blueprint('blocklist', __name__, template_folder='templates')

# صفحة الـ HTML الرئيسية
@blocklist_bp.route("/", methods=["GET"])
def home():
    return render_template("home.html")


# API مسار لإدارة الـ blocklist entries
@blocklist_bp.route("/api/blocklist", methods=["GET", "POST"])
def api_blocklist():
    if request.method == "GET":
        try:
            ips = Blocklist.query.all()
            data = []
            for ip in ips:
                data.append({
                    "id": ip.id,
                    "ip_address": ip.ip_address,
                    "comment": ip.comment,
                    "created_by": ip.created_by,
                    "added_at": ip.added_at.strftime('%Y-%m-%d %H:%M:%S') if ip.added_at else None,
                    "expires_at": ip.expires_at.strftime('%Y-%m-%d %H:%M:%S') if ip.expires_at else None,
                    "duration": ip.duration.total_seconds() / 3600 if ip.duration else None,
                    "blocks_count": ip.blocks_count or 1
                })
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "POST":
        data = request.get_json()
        try:
            ip_address = data.get("ip_address")
            comment = data.get("comment", "")
            duration_hours = int(data.get("duration", 24))
            blocks_count = int(data.get("blocks_count", 1))
            created_by = data.get("created_by")

            # تحقق من صحة IP
            ipaddress.ip_network(ip_address, strict=False)

            time_added = datetime.now(timezone.utc)
            duration = timedelta(hours=duration_hours)
            expires_at = time_added + duration

            user_id = None
            if created_by:
                user = User.query.get(created_by)
                if user:
                    user_id = user.id

            ip_entry = Blocklist(
                ip_address=ip_address,
                comment=comment,
                added_at=time_added,
                expires_at=expires_at,
                duration=duration,
                blocks_count=blocks_count,
                created_by=user_id
            )
            db.session.add(ip_entry)
            db.session.commit()

            return jsonify({"message": "IP added successfully", "id": ip_entry.id})

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400


# API مسار لتحديث IP محدد
@blocklist_bp.route("/api/blocklist/<int:entry_id>", methods=["PUT", "DELETE"])
def api_blocklist_modify(entry_id):
    ip_entry = Blocklist.query.get(entry_id)
    if not ip_entry:
        return jsonify({"error": "Entry not found"}), 404

    if request.method == "PUT":
        data = request.get_json()
        try:
            ip_address = data.get("ip_address")
            comment = data.get("comment")
            expires_at_str = data.get("expires_at")

            if ip_address:
                ipaddress.ip_network(ip_address, strict=False)
                ip_entry.ip_address = ip_address
            if comment is not None:
                ip_entry.comment = comment
            if expires_at_str:
                expires_at = datetime.strptime(expires_at_str, "%Y-%m-%dT%H:%M")
                ip_entry.expires_at = expires_at
                ip_entry.duration = expires_at - ip_entry.added_at

            db.session.commit()
            return jsonify({"message": "IP updated successfully"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400

    elif request.method == "DELETE":
        try:
            db.session.delete(ip_entry)
            db.session.commit()
            return jsonify({"message": "IP deleted successfully"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400


# API رفع CSV
@blocklist_bp.route('/api/blocklist/upload', methods=['POST'])
def upload_blocklist_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({'error': 'Invalid file'}), 400

    stream = StringIO(file.stream.read().decode("utf-8"))
    csv_input = csv.reader(stream)

    added = 0
    errors = []

    for row_num, row in enumerate(csv_input, start=1):
        if not row:
            continue

        ip_address = row[0].strip()
        comment = row[1].strip() if len(row) > 1 else ""
        duration_input = row[2].strip() if len(row) > 2 else "24"
        blocks_count_input = row[3].strip() if len(row) > 3 else "1"

        # Validate IP
        try:
            ipaddress.ip_network(ip_address, strict=False)
        except ValueError:
            errors.append(f"Row {row_num}: Invalid IP '{ip_address}'")
            continue

        # Check for duplicates
        if Blocklist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' already exists")
            continue

        # Validate duration
        try:
            duration_hours = int(duration_input)
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: Invalid duration '{duration_input}'")
            continue

        # Validate blocks_count
        try:
            blocks_count = int(blocks_count_input)
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: Invalid blocks_count '{blocks_count_input}'")
            continue

        now = datetime.now(timezone.utc)
        duration = timedelta(hours=duration_hours)
        expires_at = now + duration

        entry = Blocklist(
            ip_address=ip_address,
            comment=comment,
            added_at=now,
            expires_at=expires_at,
            duration=duration,
            blocks_count=blocks_count
        )

        db.session.add(entry)
        added += 1

    db.session.commit()
    return jsonify({'message': f'{added} IP(s) added to blocklist', 'errors': errors})
