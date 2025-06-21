import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
 
from flask import Blueprint, request, jsonify
from init_db import db
from models import Safelist, User, Blocklist
from datetime import datetime, timedelta, timezone
from markupsafe import escape
import ipaddress
import csv
from io import StringIO
from sqlalchemy import cast, String, asc, desc ,or_
from typing import Optional, Dict, Any
 
safelist_bp = Blueprint('safelist', __name__)
 
@safelist_bp.route('/', methods=['GET'])
def get_safelist():
    sort_field = request.args.get('sort', 'id')
    sort_order = request.args.get('order', 'asc')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    search_term = request.args.get('search', '')

    valid_fields = {
        'id': Safelist.id,
        'ip_address': Safelist.ip_address,
        'comment': Safelist.comment,
        'created_by': Safelist.created_by,
        'added_at': Safelist.added_at,
        'expires_at': Safelist.expires_at,
        'duration': Safelist.duration
    }

    sort_column = valid_fields.get(sort_field)
    if not sort_column:
        return jsonify({'error': f'Invalid sort field: {sort_field}'}), 400

    direction = asc if sort_order == 'asc' else desc

    query = Safelist.query
    
    # Add search filtering
    if search_term:
        query = query.filter(
            or_(
                cast(Safelist.ip_address, String).ilike(f"%{search_term}%"),
                cast(Safelist.comment, String).ilike(f"%{search_term}%"),
                cast(Safelist.created_by, String).ilike(f"%{search_term}%")
            )
        )
    
    query = query.order_by(direction(sort_column))
    total = query.count()
    entries = query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        'entries': [
            {
                'id': entry.id,
                'ip_address': entry.ip_address,
                'created_by': entry.created_by,
                'added_at': entry.added_at.strftime('%m/%d/%y, %I:%M %p') if entry.added_at else None,
                'expires_at': entry.expires_at.strftime('%m/%d/%y, %I:%M %p') if entry.expires_at else None,
                'duration': round(entry.duration.total_seconds() / 3600, 2),
                'comment': entry.comment
            } for entry in entries
        ],
        'page': page,
        'pages': (total + limit - 1) // limit,
        'total': total
    })
 
@safelist_bp.route('/index')
def index():
    return jsonify({'message': 'Safelist API endpoint - use / for data'})
 
@safelist_bp.route('/', methods=['POST'])
def add_ip():
    data = request.get_json()
    ip_address = data.get('ip_address')
    comment = escape(data.get('comment') or "")
    created_by = data.get('created_by')
    duration_input = data.get('duration')

    # Validate IP address
    if not ip_address:
        return jsonify({'error': 'IP address is required'}), 400
        
    try:
        ipaddress.ip_network(ip_address, strict=False)
    except ValueError:
        return jsonify({'error': 'Invalid IP address or subnet'}), 400

    if Safelist.query.filter_by(ip_address=ip_address).first():
        return jsonify({'error': 'IP already exists'}), 400

    if Blocklist.query.filter_by(ip_address=ip_address).first():
        return jsonify({'error': 'IP already exists in blocklist, delete it from blocklist before adding to safelist'}), 400

    # Validate duration
    if not duration_input:
        return jsonify({'error': 'Duration is required'}), 400
        
    try:
        duration_hours = int(duration_input)
        if duration_hours < 1:
            return jsonify({'error': 'Duration must be at least 1 hour'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid duration value'}), 400

    duration = timedelta(hours=duration_hours)
    added_at = datetime.now(timezone.utc)
    expires_at = added_at + duration

    # Get created_by user ID
    created_by_id: Optional[int] = None
    if created_by is not None:
        try:
            user = db.session.get(User, int(created_by))
            if user:
                created_by_id = user.id
        except (ValueError, TypeError):
            pass
    
    # If no created_by provided, use first available user
    if created_by_id is None:
        default_user = User.query.first()
        if default_user:
            created_by_id = default_user.id
        else:
            return jsonify({'error': 'No users found in system'}), 500

    # Create entry with explicit parameters (SQLAlchemy dynamic constructor)
    entry_params: Dict[str, Any] = {
        'ip_address': ip_address,
        'comment': comment,
        'added_at': added_at,
        'expires_at': expires_at,
        'duration': duration,
        'created_by': created_by_id
    }
    entry = Safelist(**entry_params)  # type: ignore[misc] # SQLAlchemy dynamic constructor

    db.session.add(entry)
    db.session.commit()
    return jsonify({'message': 'IP added successfully'}), 201
 
@safelist_bp.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '' or not (file.filename and file.filename.endswith('.csv')):
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

        try:
            ipaddress.ip_network(ip_address, strict=False)
        except ValueError:
            errors.append(f"Row {row_num}: IP '{ip_address}' was not added because it is invalid")
            continue

        if Safelist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' was not added because it already exists in the safelist")
            continue

        if Blocklist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' was not added because it exists in the blocklist")
            continue

        try:
            duration_hours = int(duration_input)
            if duration_hours < 1:
                errors.append(f"Row {row_num}: IP '{ip_address}' was not added because duration must be at least 1 hour")
                continue
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: IP '{ip_address}' was not added because the duration '{duration_input}' is invalid")
            continue

        now = datetime.now(timezone.utc)
        duration = timedelta(hours=duration_hours)
        expires_at = now + duration

        # Get default user for created_by field
        default_user = User.query.first()
        default_user_id = default_user.id if default_user else 1

        # Create entry with explicit parameters (SQLAlchemy dynamic constructor)
        entry_params: Dict[str, Any] = {
            'ip_address': ip_address,
            'comment': comment,
            'added_at': now,
            'expires_at': expires_at,
            'duration': duration,
            'created_by': default_user_id
        }
        entry = Safelist(**entry_params)  # type: ignore[misc] # SQLAlchemy dynamic constructor

        db.session.add(entry)
        added += 1

    db.session.commit()
    return jsonify({'message': f'{added} IP(s) added', 'errors': errors})
 
@safelist_bp.route('/<int:entry_id>', methods=['PUT'])
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

        if entry.added_at.tzinfo is None:
            entry.added_at = entry.added_at.replace(tzinfo=timezone.utc)

        entry.duration = entry.expires_at - entry.added_at

        if entry.duration.total_seconds() < 3600:
            return jsonify({'error': 'Updated duration must be at least 1 hour'}), 400

    entry.comment = comment or entry.comment
    db.session.commit()
    return jsonify({'message': 'IP updated successfully'})
 
@safelist_bp.route('/<int:entry_id>', methods=['DELETE'])
def delete_ip(entry_id):
    entry = Safelist.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'IP deleted successfully'})
 
@safelist_bp.route('/search', methods=['GET'])
def search_ip():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
 
    results = Safelist.query.filter(
        or_(
            cast(Safelist.ip_address, String).ilike(f"%{query}%"),
            cast(Safelist.comment, String).ilike(f"%{query}%"),
            cast(Safelist.created_by, String).ilike(f"%{query}%")
        )
    ).all()
 
    return jsonify([
        {
            'id': entry.id,
            'ip_address': str(entry.ip_address),
            'created_by': entry.created_by,
            'added_at': entry.added_at.strftime('%m/%d/%y, %I:%M %p') if entry.added_at else None,
            'expires_at': entry.expires_at.strftime('%m/%d/%y, %I:%M %p') if entry.expires_at else None,
            'duration': round(entry.duration.total_seconds() / 3600, 2),
            'comment': entry.comment
        }
        for entry in results
    ])