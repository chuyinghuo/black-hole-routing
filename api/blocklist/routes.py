import ipaddress
from flask import Blueprint, render_template, request, redirect, current_app, jsonify
from datetime import datetime, timedelta, timezone
import sys
import os
from io import StringIO
import csv
from init_db import db
from models import Blocklist, User, Safelist, BlockHistory
from sqlalchemy import cast, String, asc, desc, or_
from ipaddress import ip_network
from urllib.parse import quote_plus

# Add project root to sys.path for module access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

blocklist_bp = Blueprint('blocklist', __name__, template_folder='templates')


@blocklist_bp.route("/", methods=["GET", "POST"])
def home():
    try:
        if request.method == "POST":
            data = request.get_json() or request.form

            time_added_str = data.get("time_added")
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

            # Check if IP exists in Safelist
            if Safelist.query.filter_by(ip_address=ip_address).first():
                return jsonify({'error': 'IP already exists in safelist, delete it from safelist before adding to blocklist'}), 400

            # Check if IP already exists in Blocklist
            existing_entry = Blocklist.query.filter_by(ip_address=ip_address).first()
            if existing_entry:
                existing_entry.blocks_count += 1
                existing_entry.added_at = datetime.utcnow()
                existing_entry.expires_at = time_unblocked
                existing_entry.duration = duration
                existing_entry.comment = comment

                history_entry = BlockHistory(
                    ip_address=ip_address,
                    created_by=existing_entry.created_by,
                    comment=existing_entry.comment,
                    added_at=datetime.utcnow(),
                    unblocked_at=existing_entry.expires_at,
                )
                db.session.add(history_entry)
                db.session.commit()
                return jsonify({'message': 'IP already existed, updated block count and time.'}), 200

            # Otherwise, add new blocklist entry
            created_by = None
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
                added_at=time_added,
                expires_at=time_unblocked,
                duration=duration,
                comment=comment,
                created_by=created_by
            )
            db.session.add(ip_entry)
            db.session.commit()
            return jsonify({'message': 'IP added successfully'}), 201

    except Exception as e:
        print(f"Error adding IP: {e}")
        db.session.rollback()

    # GET method: listing and searching
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

    message = request.args.get("message")
    return render_template("blocklist.html", ips=ips, message=message)


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

        if not ip_entry:
            return redirect("/blocklist/?message=IP+not+found")

        ip_entry.ip_address = request.form.get("ip_address")
        ip_entry.comment = request.form.get("comment")
        ip_entry.added_at = datetime.utcnow()
        ip_entry.expires_at = datetime.strptime(request.form.get("time_unblocked"), "%Y-%m-%dT%H:%M")
        if not request.form.get("time_unblocked"):
            return redirect("/blocklist/?message=Time+Unblocked+is+required")
        added_at = ip_entry.added_at.replace(tzinfo=None)
        ip_entry.duration = ip_entry.expires_at - ip_entry.added_at

        if ip_entry.duration.total_seconds() < 3600:
            return redirect("/blocklist/?message=Duration+must+be+at+least+1+hour")


        db.session.commit()
        return redirect("/blocklist/?message=IP+updated+successfully")

    except Exception as e:
        print(f"Error updating IP: {e}")
        db.session.rollback()
        return redirect("/blocklist/?message=Error+updating+IP")


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
    from ipaddress import ip_network  # Ensure local import to override global if needed
    from urllib.parse import quote_plus

    if "file" not in request.files:
        return redirect("/blocklist/?message=" + quote_plus("No file uploaded"))

    file = request.files["file"]
    if file.filename == '' or not file.filename.endswith('.csv'):
        return redirect("/blocklist/?message=" + quote_plus("Invalid file format"))

    try:
        stream = StringIO(file.stream.read().decode("utf-8"))
        csv_input = csv.DictReader(stream)
    except Exception as e:
        return redirect("/blocklist/?message=" + quote_plus(f"CSV parse error: {str(e)}"))

    added = 0
    errors = []

    for row_num, row in enumerate(csv_input, start=2):
        raw_ip = row.get("ip_address", "").strip()
        try:
            ip_address = str(ip_network(raw_ip, strict=False))
        except ValueError:
            errors.append(f"Row {row_num}: Invalid IP or subnet '{raw_ip}'")
            continue

        comment = row.get("comment", "").strip()
        duration_input = row.get("duration", "24").strip()

        if Blocklist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' already exists in blocklist")
            continue

        if Safelist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' exists in safelist")
            continue

        try:
            duration_hours = int(duration_input)
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: Invalid duration '{duration_input}'")
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
            blocks_count=1,
            created_by=None
        )

        try:
            db.session.add(entry)
            added += 1
        except Exception as e:
            db.session.rollback()
            errors.append(f"Row {row_num}: DB error → {str(e)}")

    db.session.commit()

    message = f"{added} IP(s) added"
    if errors:
        detailed_errors = " | ".join(errors)
        message += f" with {len(errors)} error(s): {detailed_errors}"

    return redirect("/blocklist/?message=" + quote_plus(message))

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