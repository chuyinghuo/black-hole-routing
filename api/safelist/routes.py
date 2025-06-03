from flask import Blueprint, request, jsonify, render_template
from api.models import SafeList, db
from datetime import datetime
from markupsafe import escape
import ipaddress
import csv
from io import StringIO
from datetime import datetime, timedelta


safelist_bp = Blueprint('safelist', __name__)

@safelist_bp.route('/api/safelist', methods=['GET'])
def get_safelist():
    entries = SafeList.query.all()
    return jsonify([{
        'id': entry.id,
        'ip_address': entry.ip_address,
        'user_id': entry.user_id,
        'created_at': entry.created_at.isoformat() if entry.created_at else None,
        'ending_date': entry.ending_date.isoformat() if entry.ending_date else None,
        'duration': entry.duration,
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
    user_id = data.get('user_id')
    duration = data.get('duration')  # بالـ ساعات
    try:
        ipaddress.ip_network(ip_address, strict=False)
    except ValueError:
        return jsonify({'error': 'Invalid IP address or subnet'}), 400

    if SafeList.query.filter_by(ip_address=ip_address).first():
        return jsonify({'error': 'IP already exists'}), 400

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid duration value'}), 400

    created_at = datetime.now()
    ending_date = created_at + timedelta(hours=duration)

    entry = SafeList(
        ip_address=ip_address,
        comment=comment,
        user_id=user_id,
        created_at=created_at,
        ending_date=ending_date,
        duration=duration
    )
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

        if SafeList.query.filter_by(ip_address=ip_address).first():
            errors.append(f"Row {row_num}: IP '{ip_address}' already exists")
            continue

        entry = SafeList(ip_address=ip_address, comment=comment)
        db.session.add(entry)
        added += 1

    db.session.commit()
    return jsonify({'message': f'{added} IP(s) added successfully.', 'errors': errors})

@safelist_bp.route('/api/safelist/<string:entry_id>', methods=['PUT'])
def edit_ip(entry_id):
    data = request.get_json()
    entry = SafeList.query.get_or_404(entry_id)

    ip_address = data.get('ip_address')
    comment = data.get('comment')
    ending_date_str = data.get('ending_date')

    if ip_address:
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            return jsonify({'error': 'Invalid IP address'}), 400
        if SafeList.query.filter(SafeList.ip_address == ip_address, SafeList.id != entry_id).first():
            return jsonify({'error': 'IP already exists'}), 400
        entry.ip_address = ip_address

    if ending_date_str:
        try:
            entry.ending_date = datetime.fromisoformat(ending_date_str)
        except ValueError:
            return jsonify({'error': 'Invalid ending_date format'}), 400

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

    entry = SafeList.query.filter_by(ip_address=ip).first()
    if not entry:
        return jsonify({'message': 'IP not found'}), 404

    return jsonify({
        'id': entry.id,
        'ip_address': entry.ip_address,
        'user_id': entry.user_id,
        'created_at': entry.created_at.isoformat() if entry.created_at else None,
        'ending_date': entry.ending_date.isoformat() if entry.ending_date else None,
        'duration': entry.duration,
        'comment': entry.comment
    })

@safelist_bp.route('/api/safelist/<string:entry_id>', methods=['DELETE'])
def delete_ip(entry_id):
    entry = SafeList.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'IP deleted successfully'})

@safelist_bp.route('/api/safelist/remove', methods=['POST'])
def remove_ips():
    data = request.get_json()
    ids = data.get('ids')
    if not ids or not isinstance(ids, list):
        return jsonify({'error': 'A list of IDs is required'}), 400

    entries = SafeList.query.filter(SafeList.id.in_(ids)).all()
    if not entries:
        return jsonify({'message': 'No matching entries found'}), 404

    for entry in entries:
        db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': f'Successfully removed {len(entries)} IP(s)'})

@safelist_bp.route('/ip-list')
def ip_list():
    return render_template('ip_list.html')