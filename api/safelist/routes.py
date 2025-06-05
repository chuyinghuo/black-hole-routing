from flask import Blueprint, request, jsonify, render_template
from models import Safelist, User, db
from datetime import datetime, timedelta
from markupsafe import escape
import ipaddress
import csv
from io import StringIO

safelist_bp = Blueprint('safelist', __name__)

@safelist_bp.route('/api/safelist', methods=['GET'])
def get_safelist():
    entries = Safelist.query.all()
    return jsonify([{
        'id': entry.id,
        'ip_address': entry.ip_address,
        'created_by': entry.created_by,
        'added_at': entry.added_at.isoformat() if entry.added_at else None,
        'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
        'duration': str(entry.duration),
        'comment': entry.comment
    } for entry in entries])

@safelist_bp.route('/')
def index():
    return render_template('ip_list.html')

@safelist_bp.route('/api/safelist', methods=['POST'])
def add_ip():
    data = request.get_json()
    ip_address = data.get('ip_address')
    comment = escape(data.get('comment'))
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
        duration = timedelta(hours=duration_hours)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid duration value'}), 400

    added_at = datetime.utcnow()
    expires_at = added_at + duration

    entry = Safelist(
        ip_address=ip_address,
        comment=comment,
        added_at=added_at,
        expires_at=expires_at,
        duration=duration
    )

    # Only set `created_by` if the user ID exists in the users table
    if created_by is not None:
        user = db.session.get(User, created_by)
        if user:
            entry.created_by = created_by

    db.session.add(entry)
    db.session.commit()
    return jsonify({'message': 'IP added successfully'}), 201

@safelist_bp.route('/api/safelist/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400

    stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)

    added = 0
    errors = []

    for row_num, row in enumerate(csv_input, start=1):
        if not row:
            continue
        ip_address = row[0].strip()
        comment = row[1].strip() if len(row) > 1 else None

        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            errors.append(f"Row {row_num}: Invalid IP '{ip_address}'")
            continue

        if Safelist.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' already exists")
            continue

        entry = Safelist(
            ip_address=ip_address,
            comment=comment,
            duration=timedelta(hours=24),
            added_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.session.add(entry)
        added += 1

    db.session.commit()
    return jsonify({'message': f'{added} IP(s) added successfully.', 'errors': errors})

@safelist_bp.route('/api/safelist/<string:entry_id>', methods=['PUT'])
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
            entry.expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
            return jsonify({'error': 'Invalid expires_at format'}), 400

    entry.comment = comment
    db.session.commit()
    return jsonify({'message': 'IP updated successfully'})

@safelist_bp.route('/api/safelist/search', methods=['GET'])
def search_ip():
    ip = request.args.get('ip')
    if not ip:
        return jsonify({'error': 'IP parameter is required'}), 400

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return jsonify({'error': 'Invalid IP address'}), 400

    entry = Safelist.query.filter_by(ip_address=ip).first()
    if not entry:
        return jsonify({'message': 'IP not found'}), 404

    return jsonify({
        'id': entry.id,
        'ip_address': entry.ip_address,
        'created_by': entry.created_by,
        'added_at': entry.added_at.isoformat() if entry.added_at else None,
        'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
        'duration': str(entry.duration),
        'comment': entry.comment
    })

@safelist_bp.route('/api/safelist/<string:entry_id>', methods=['DELETE'])
def delete_ip(entry_id):
    entry = Safelist.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'IP deleted successfully'})

@safelist_bp.route('/api/safelist/remove', methods=['POST'])
def remove_ips():
    data = request.get_json()
    ids = data.get('ids')
    if not ids or not isinstance(ids, list):
        return jsonify({'error': 'A list of IDs is required'}), 400

    entries = Safelist.query.filter(Safelist.id.in_(ids)).all()
    if not entries:
        return jsonify({'message': 'No matching entries found'}), 404

    for entry in entries:
        db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': f'Successfully removed {len(entries)} IP(s)'})