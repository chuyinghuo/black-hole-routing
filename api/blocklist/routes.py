import ipaddress
from flask import Blueprint, render_template, request, redirect, current_app, jsonify
from datetime import datetime, timedelta, timezone
import sys
import os
from io import StringIO
import csv
from init_db import db
from models import Blocklist, User, Safelist
from sqlalchemy import cast, String, asc, desc, or_

# Add project root to sys.path for module access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

blocklist_bp = Blueprint('blocklist', __name__, template_folder='templates')

@blocklist_bp.route("/", methods=["GET", "POST"])
def home():
    try:
        if request.method == "POST":
            data = request.get_json() or request.form
            # Parse time fields
            time_added_str = data.get("time_added")  # likely to be None
            duration_input = data.get("duration")
            time_added = datetime.strptime(time_added_str, "%Y-%m-%dT%H:%M") if time_added_str else datetime.utcnow()

            try:
                duration_hours = int(duration_input)
            except (ValueError, TypeError):
                duration_hours = 24

            duration = timedelta(hours=duration_hours)
            time_unblocked = time_added + duration

            ip_address = data.get("ip_address")
            comment = data.get("comment") or ""
            try:
                blocks_count = int(data.get("blocks_count"))
            except (ValueError, TypeError):
                blocks_count = 1
            created_by_input = data.get("created_by")

            try:
                ipaddress.ip_network(ip_address, strict=False)
            except ValueError:
                return jsonify({'error': 'Invalid IP address or subnet'}), 400

            if Blocklist.query.filter_by(ip_address=ip_address).first():
                return jsonify({'error': 'IP already exists in blocklist'}), 400

            if Safelist.query.filter_by(ip_address=ip_address).first():
                return jsonify({'error': 'IP already exists in safelist, delete it from safelist before adding to blocklist'}), 400

            created_by = None
            created_by_input = request.form.get("created_by")
            if created_by_input:
                try:
                    user_id = int(created_by_input)
                    user = User.query.get(user_id)
                    if user:
                        created_by = user.id
                except ValueError:
                    pass

            ip_entry = Blocklist(
                ip_address=ip_address,
                blocks_count=blocks_count,
                added_at=time_added.strftime('%m/%d/%y, %I:%M %p') if time_added else None,
                expires_at=time_unblocked.strftime('%m/%d/%y, %I:%M %p') if time_unblocked else None,
                duration=duration,
                comment=comment,
                created_by=created_by
            )
            db.session.add(ip_entry)
            db.session.commit()
            return jsonify({'message': 'IP added successfully'}), 201
        else:
            db.session.rollback()
    except Exception as e:
        print(f"Error adding IP: {e}")
        db.session.rollback()

    try:
        search_term = request.args.get("search", "").strip()
        sort_column = request.args.get("sort", "added_at")
        sort_order = request.args.get("order", "desc")

        valid_columns = {
            "ip_address": Blocklist.ip_address,
            "blocks_count": Blocklist.blocks_count,
            "added_at": Blocklist.added_at,
            "expires_at": Blocklist.expires_at,
            "comment": Blocklist.comment,
            "created_by": Blocklist.created_by,
            "duration": Blocklist.duration
        }

        sort_expr = valid_columns.get(sort_column, Blocklist.added_at)
        sort_expr = asc(sort_expr) if sort_order == "asc" else desc(sort_expr)

        if search_term:
            ips = Blocklist.query.filter(
                or_(
                    cast(Blocklist.ip_address, String).ilike(f"%{search_term}%"),
                    cast(Blocklist.comment, String).ilike(f"%{search_term}%"),
                    cast(Blocklist.created_by, String).ilike(f"%{search_term}%")
                )
            ).order_by(sort_expr).all()
        else:
            ips = Blocklist.query.order_by(sort_expr).all()

    except Exception as e:
        print(f"Error fetching IPs: {e}")
        ips = []

    return render_template("blocklist.html", ips=ips)


@blocklist_bp.route("/search", methods=["GET"])
def search_ip():
    query = request.args.get("ip")
    if not query:
        return jsonify({'error': 'No IP address provided'}), 400

    results = Blocklist.query.filter(Blocklist.ip_address.like(f"%{query}%")).all()

    return jsonify([
        {
            'id': entry.id,
            'ip_address': entry.ip_address,
            'blocks_count': entry.blocks_count,
            'added_at': entry.added_at,
            'expires_at': entry.expires_at,
            'comment': entry.comment,
            'created_by': entry.created_by,
            'duration': entry.duration.total_seconds() / 3600 if entry.duration else None
        } for entry in results
    ])


@blocklist_bp.route("/update", methods=["POST"])
def update():
    try:
        entry_id = request.form.get("entry_id")
        ip_entry = Blocklist.query.get(entry_id)

        if ip_entry:
            ip_entry.ip_address = request.form.get("ip_address")
            ip_entry.comment = request.form.get("comment")
            ip_entry.added_at = datetime.strptime(request.form.get("time_added"), "%Y-%m-%dT%H:%M")
            ip_entry.expires_at = datetime.strptime(request.form.get("time_unblocked"), "%Y-%m-%dT%H:%M")
            ip_entry.duration = ip_entry.expires_at - ip_entry.added_at

            try:
                ip_entry.blocks_count = int(request.form.get("blocks_count"))
            except (ValueError, TypeError):
                ip_entry.blocks_count = 1

            created_by_input = request.form.get("created_by")
            if created_by_input:
                try:
                    user_id = int(created_by_input)
                    user = User.query.get(user_id)
                    ip_entry.created_by = user.id if user else None
                except ValueError:
                    ip_entry.created_by = None

            db.session.commit()
    except Exception as e:
        print(f"Error updating IP: {e}")
        db.session.rollback()
    return redirect("/blocklist/")


@blocklist_bp.route("/delete", methods=["POST"])
def delete():
    try:
        entry_id = request.form.get("entry_id")
        ip_entry = Blocklist.query.get(entry_id)
        if ip_entry:
            db.session.delete(ip_entry)
            db.session.commit()
    except Exception as e:
        print(f"Error deleting IP: {e}")
        db.session.rollback()
    return redirect("/blocklist/")


@blocklist_bp.route("/upload_csv", methods=["POST"])
def upload_blocklist_csv():
    if "file" not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files["file"]
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

        try:
            ipaddress.ip_network(ip_address, strict=False)
        except ValueError:
            errors.append(f"Row {row_num}: Invalid IP '{ip_address}'")
            continue

        if Blocklist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' already exists in blocklist")
            continue

        if Safelist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' already exists in safelist")
            continue

        try:
            duration_hours = int(duration_input)
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: Invalid duration '{duration_input}'")
            continue

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
    return jsonify({
        'message': f'{added} IP(s) added to blocklist',
        'errors': errors
    })


@blocklist_bp.route("/delete_bulk", methods=["POST"])
def bulk_delete():
    data = request.get_json()
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"error": "No IDs provided"}), 400

    try:
        for entry_id in ids:
            ip_entry = Blocklist.query.get(entry_id)
            if ip_entry:
                db.session.delete(ip_entry)
        db.session.commit()
        return jsonify({"message": f"Deleted {len(ids)} entries."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Deletion failed: {str(e)}"}), 500