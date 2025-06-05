import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Blueprint, request, jsonify, render_template
from init_db import db
from models import Safelist, User
from datetime import datetime, timedelta, timezone
from markupsafe import escape
import ipaddress
import csv
from io import StringIO

safelist_bp = Blueprint('safelist', __name__)

@safelist_bp.route('/api/safelist', methods=['GET'])
def get_safelist():
    from flask import current_app
    print(f"[DEBUG] App context active: {current_app.name}")
    entries = Safelist.query.all()
    return jsonify([
        {
            'id': entry.id,
            'ip_address': entry.ip_address,
            'created_by': entry.created_by,
            'added_at': entry.added_at.isoformat() if entry.added_at else None,
            'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
            'duration': str(entry.duration),
            'comment': entry.comment
        }
        for entry in entries
    ])

@safelist_bp.route('/')
def index():
    return render_template('ip_list.html')

@safelist_bp.route('/api/safelist', methods=['POST'])
def add_ip():
    data = request.get_json()
    ip_address = data.get('ip_address')
    comment = escape(data.get('comment') or "")
    created_by = data.get('created_by')
    duration_input = data.get('duration')

    try:
        ipaddress.ip_network(ip_address, strict=False)
    except ValueError:
        return jsonify({'error': 'Invalid IP address or subnet'}), 400

    if Safelist.query.filter_by(ip_address=ip_address).first():
        return jsonify({'error': 'IP already exists'}), 400

    try:
        duration_hours = int(duration_input)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid duration value'}), 400

    duration = timedelta(hours=duration_hours)
    added_at = datetime.now(timezone.utc)
    expires_at = added_at + duration

    entry = Safelist(
        ip_address=ip_address,
        comment=comment,
        added_at=added_at,
        expires_at=expires_at,
        duration=duration
    )

    if created_by is not None:
        try:
            user = db.session.get(User, int(created_by))
            if user:
                entry.created_by = user.id
        except (ValueError, TypeError):
            pass

    db.session.add(entry)
    db.session.commit()
    return jsonify({'message': 'IP added successfully'}), 201

@safelist_bp.route('/api/safelist/upload', methods=['POST'])
def upload_csv():
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

        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            errors.append(f"Row {row_num}: Invalid IP '{ip_address}'")
            continue

        if Safelist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' already exists")
            continue

        now = datetime.now(timezone.utc)
        entry = Safelist(
            ip_address=ip_address,
            comment=comment,
            added_at=now,
            expires_at=now + timedelta(hours=24),
            duration=timedelta(hours=24)
        )
        db.session.add(entry)
        added += 1

    db.session.commit()
    return jsonify({'message': f'{added} IP(s) added', 'errors': errors})

@safelist_bp.route('/api/safelist/<int:entry_id>', methods=['PUT'])
def edit_ip(entry_id):
    data = request.get_json()
    entry = Safelist.query.get_or_404(entry_id)

    ip_address = data.get('ip_address')
    comment = data.get('comment')
    expires_at_str = data.get('expires_at')

    if ip_address:
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            return jsonify({'error': 'Invalid IP address'}), 400
        if Safelist.query.filter(Safelist.ip_address == ip_address, Safelist.id != entry_id).first():
            return jsonify({'error': 'IP already exists'}), 400
        entry.ip_address = ip_address

    if expires_at_str:
        try:
            parsed_expires_at = datetime.fromisoformat(expires_at_str)
            if parsed_expires_at.tzinfo is None:
                parsed_expires_at = parsed_expires_at.replace(tzinfo=timezone.utc)
            entry.expires_at = parsed_expires_at
        except ValueError:
            return jsonify({'error': 'Invalid expires_at format'}), 400

        # Ensure added_at is also timezone-aware for subtraction
        if entry.added_at.tzinfo is None:
            entry.added_at = entry.added_at.replace(tzinfo=timezone.utc)

        entry.duration = entry.expires_at - entry.added_at

    entry.comment = comment or entry.comment
    db.session.commit()
    return jsonify({'message': 'IP updated successfully'})

@safelist_bp.route('/api/safelist/<int:entry_id>', methods=['DELETE'])
def delete_ip(entry_id):
    entry = Safelist.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'IP deleted successfully'})

@safelist_bp.route('/api/safelist/search', methods=['GET'])
def search_ip():
    ip = request.args.get('ip')
    if not ip:
        return jsonify({'error': 'IP parameter is required'}), 400

    results = Safelist.query.filter(Safelist.ip_address.like(f"%{ip}%")).all()
    return jsonify([
        {
            'id': entry.id,
            'ip_address': entry.ip_address,
            'created_by': entry.created_by,
            'added_at': entry.added_at.isoformat() if entry.added_at else None,
            'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
            'duration': str(entry.duration),
            'comment': entry.comment
        }
        for entry in results
    ])
