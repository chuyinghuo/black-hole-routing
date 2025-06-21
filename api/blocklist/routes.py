import ipaddress
from flask import Blueprint, request, redirect, current_app, jsonify
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
from typing import Optional, Dict, Any
import asyncio

# Add project root to sys.path for module access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ai-scout')))

# Import IP Guardian
try:
    from ai_scout.ip_guardian import IPGuardianAgent
    GUARDIAN_AVAILABLE = True
    guardian_instance = None  # Will be initialized when needed
    GUARDIAN_INITIALIZED = False
    print("✅ IP Guardian module loaded successfully")
except ImportError as e:
    GUARDIAN_AVAILABLE = False
    GUARDIAN_INITIALIZED = False
    guardian_instance = None
    print(f"⚠️  IP Guardian not available: {e}")

blocklist_bp = Blueprint('blocklist', __name__, template_folder='templates')

# Global Guardian settings
guardian_enabled = True  # Enable Guardian by default

def get_guardian():
    """Get or initialize the Guardian instance"""
    global guardian_instance, GUARDIAN_INITIALIZED
    if guardian_instance is None and GUARDIAN_AVAILABLE:
        try:
            guardian_instance = IPGuardianAgent()
            GUARDIAN_INITIALIZED = True
            print("✅ IP Guardian initialized successfully")
        except Exception as e:
            print(f"Failed to initialize IP Guardian: {e}")
            GUARDIAN_INITIALIZED = False
    return guardian_instance

async def validate_with_guardian(ip_address: str, bulk_operation: bool = False) -> Dict[str, Any]:
    """Validate an IP address with the Guardian"""
    if not guardian_enabled or not GUARDIAN_AVAILABLE:
        return {'allowed': True, 'reason': 'Guardian disabled'}
    
    try:
        guard = get_guardian()
        if guard is None:
            return {'allowed': True, 'reason': 'Guardian not available'}
        
        # Prepare context for Guardian
        context = {'bulk_operation': bulk_operation} if bulk_operation else None
        result = await guard.validate_blocklist_addition(ip_address, context)
        return result
    except Exception as e:
        print(f"Guardian validation error: {e}")
        return {'allowed': True, 'reason': f'Guardian error: {str(e)}'}

@blocklist_bp.route("/guardian/status", methods=["GET"])
def guardian_status():
    """Get Guardian status and configuration"""
    return jsonify({
        'available': GUARDIAN_AVAILABLE,
        'enabled': guardian_enabled,
        'guardian_initialized': GUARDIAN_INITIALIZED and guardian_instance is not None
    })

@blocklist_bp.route("/guardian/toggle", methods=["POST"])
def toggle_guardian():
    """Toggle Guardian on/off"""
    global guardian_enabled
    data = request.get_json()
    
    if not GUARDIAN_AVAILABLE:
        return jsonify({'error': 'Guardian not available. Install required dependencies.'}), 400
    
    guardian_enabled = data.get('enabled', False)
    
    # Initialize guardian if enabling
    if guardian_enabled:
        guard = get_guardian()
        if guard is None:
            return jsonify({'error': 'Failed to initialize Guardian'}), 500
    
    return jsonify({
        'enabled': guardian_enabled,
        'message': f'Guardian {"enabled" if guardian_enabled else "disabled"}'
    })

@blocklist_bp.route("/guardian/validate", methods=["POST"])
def validate_ip():
    """Validate a single IP address with Guardian"""
    data = request.get_json()
    ip_address = data.get('ip_address')
    
    if not ip_address:
        return jsonify({'error': 'IP address required'}), 400
    
    if not GUARDIAN_AVAILABLE:
        return jsonify({
            'allowed': True,
            'reason': 'Guardian not available',
            'risk_level': 'UNKNOWN'
        })
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(validate_with_guardian(ip_address))
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Validation failed: {str(e)}'}), 500

@blocklist_bp.route("/", methods=["GET", "POST"])
def home():
    try:
        if request.method == "POST":
            data = request.get_json() or request.form

            time_added_str = data.get("time_added")
            duration_input = data.get("duration")
            time_added = datetime.strptime(time_added_str, "%Y-%m-%dT%H:%M") if time_added_str else datetime.utcnow()

            # Validate and convert duration
            if duration_input is not None:
                try:
                    duration_hours = int(duration_input)
                except (ValueError, TypeError):
                    duration_hours = 24
            else:
                duration_hours = 24

            duration = timedelta(hours=duration_hours)
            time_unblocked = time_added + duration

            ip_address = data.get("ip_address")
            comment = data.get("comment") or ""

            # Validate and convert blocks_count
            blocks_count_input = data.get("blocks_count")
            if blocks_count_input is not None:
                try:
                    blocks_count = int(blocks_count_input)
                except (ValueError, TypeError):
                    blocks_count = 1
            else:
                blocks_count = 1

            created_by_input = data.get("created_by")

            # Validate IP address
            if ip_address:
                try:
                    ipaddress.ip_network(ip_address, strict=False)
                except ValueError:
                    return jsonify({'error': 'Invalid IP address or subnet'}), 400
            else:
                return jsonify({'error': 'IP address is required'}), 400

            # Guardian validation with override support
            override_guardian = data.get('override_guardian', False)
            
            if GUARDIAN_AVAILABLE and guardian_enabled and not override_guardian:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    validation = loop.run_until_complete(validate_with_guardian(ip_address))
                    loop.close()
                    
                    if not validation['allowed']:
                        return jsonify({
                            'error': 'Guardian prevented block',
                            'reason': validation.get('recommendation', 'Blocked by Guardian'),
                            'risk_level': validation.get('risk_level', 'UNKNOWN'),
                            'confidence': validation.get('confidence', 0),
                            'guardian_block': True,
                            'can_override': True,
                            'detailed_explanation': validation.get('recommendation', 'Blocked by Guardian')
                        }), 403
                except Exception as e:
                    print(f"Guardian validation error: {e}")
                    # Continue with blocking if Guardian fails

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

                # Create BlockHistory entry with explicit parameters (SQLAlchemy dynamic constructor)
                history_params: Dict[str, Any] = {
                    'ip_address': ip_address,
                    'created_by': existing_entry.created_by,
                    'comment': existing_entry.comment,
                    'added_at': datetime.utcnow(),
                    'unblocked_at': existing_entry.expires_at,
                }
                history_entry = BlockHistory(**history_params)  # type: ignore[misc] # SQLAlchemy dynamic constructor
                db.session.add(history_entry)
                db.session.commit()
                return jsonify({'message': 'IP already existed, updated block count and time.'}), 200

            # Otherwise, add new blocklist entry
            created_by: Optional[int] = None
            if created_by_input:
                try:
                    user_id = int(created_by_input)
                    user = User.query.get(user_id)
                    if user:
                        created_by = user.id
                except ValueError:
                    pass

            # Create Blocklist entry with explicit parameters (SQLAlchemy dynamic constructor)
            blocklist_params: Dict[str, Any] = {
                'ip_address': ip_address,
                'blocks_count': blocks_count,
                'added_at': time_added,
                'expires_at': time_unblocked,
                'duration': duration,
                'comment': comment,
                'created_by': created_by
            }
            ip_entry = Blocklist(**blocklist_params)  # type: ignore[misc] # SQLAlchemy dynamic constructor
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

    # Check if this is an API request (Accept header contains 'application/json' or from React)
    if (request.headers.get('Accept', '').find('application/json') != -1 or 
        request.headers.get('User-Agent', '').find('axios') != -1):
        # Return JSON response for API requests
        return jsonify([
            {
                'id': entry.id,
                'ip_address': entry.ip_address,
                'blocks_count': entry.blocks_count,
                'added_at': entry.added_at.isoformat() if entry.added_at else None,
                'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
                'comment': entry.comment,
                'created_by': entry.created_by,
                'duration': entry.duration.total_seconds() / 3600 if entry.duration else None
            } for entry in ips
        ])

    # For any non-API requests, still return JSON (no more templates)
    return jsonify([
        {
            'id': entry.id,
            'ip_address': entry.ip_address,
            'blocks_count': entry.blocks_count,
            'added_at': entry.added_at.isoformat() if entry.added_at else None,
            'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
            'comment': entry.comment,
            'created_by': entry.created_by,
            'duration': entry.duration.total_seconds() / 3600 if entry.duration else None
        } for entry in ips
    ])


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
        # Support both form data and JSON
        if request.is_json:
            data = request.get_json()
            entry_id = data.get("entry_id")
            ip_address = data.get("ip_address")
            comment = data.get("comment")
            time_unblocked = data.get("time_unblocked")
        else:
            entry_id = request.form.get("entry_id")
            ip_address = request.form.get("ip_address")
            comment = request.form.get("comment")
            time_unblocked = request.form.get("time_unblocked")

        ip_entry = Blocklist.query.get(entry_id)
        if not ip_entry:
            if request.is_json or request.headers.get('Accept', '').find('application/json') != -1:
                return jsonify({"error": "IP not found"}), 404
            return redirect("/blocklist/?message=IP+not+found")

        if not time_unblocked:
            if request.is_json or request.headers.get('Accept', '').find('application/json') != -1:
                return jsonify({"error": "Time unblocked is required"}), 400
            return redirect("/blocklist/?message=Time+Unblocked+is+required")

        ip_entry.ip_address = ip_address
        ip_entry.comment = comment
        ip_entry.added_at = datetime.utcnow()
        ip_entry.expires_at = datetime.strptime(time_unblocked, "%Y-%m-%dT%H:%M")
        added_at = ip_entry.added_at.replace(tzinfo=None)
        ip_entry.duration = ip_entry.expires_at - ip_entry.added_at

        if ip_entry.duration.total_seconds() < 3600:
            if request.is_json or request.headers.get('Accept', '').find('application/json') != -1:
                return jsonify({"error": "Duration must be at least 1 hour"}), 400
            return redirect("/blocklist/?message=Duration+must+be+at+least+1+hour")

        db.session.commit()
        
        if request.is_json or request.headers.get('Accept', '').find('application/json') != -1:
            return jsonify({"message": "IP updated successfully"}), 200
        return redirect("/blocklist/?message=IP+updated+successfully")

    except Exception as e:
        print(f"Error updating IP: {e}")
        db.session.rollback()
        if request.is_json or request.headers.get('Accept', '').find('application/json') != -1:
            return jsonify({"error": f"Error updating IP: {str(e)}"}), 500
        return redirect("/blocklist/?message=Error+updating+IP")


@blocklist_bp.route("/delete", methods=["POST"])
def delete():
    try:
        # Support both form data and JSON
        if request.is_json:
            data = request.get_json()
            entry_id = data.get("entry_id")
        else:
            entry_id = request.form.get("entry_id")
        
        ip_entry = Blocklist.query.get(entry_id)
        if ip_entry:
            db.session.delete(ip_entry)
            db.session.commit()
            
        # Return JSON for API requests
        if request.is_json or request.headers.get('Accept', '').find('application/json') != -1:
            return jsonify({"message": "Entry deleted successfully"}), 200
            
    except Exception as e:
        print(f"Error deleting IP: {e}")
        db.session.rollback()
        if request.is_json or request.headers.get('Accept', '').find('application/json') != -1:
            return jsonify({"error": f"Failed to delete entry: {str(e)}"}), 500
            
    return redirect("/blocklist/")


@blocklist_bp.route("/upload_csv", methods=["POST"])
def upload_blocklist_csv():
    from ipaddress import ip_network  # Ensure local import to override global if needed
    from urllib.parse import quote_plus

    if "file" not in request.files:
        return redirect("/blocklist/?message=" + quote_plus("No file uploaded"))

    file = request.files["file"]
    if not file.filename or file.filename == '' or not file.filename.endswith('.csv'):
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

        # Create Blocklist entry with explicit parameters (SQLAlchemy dynamic constructor)
        entry_params: Dict[str, Any] = {
            'ip_address': ip_address,
            'comment': comment,
            'added_at': now,
            'expires_at': expires_at,
            'duration': duration,
            'blocks_count': 1,
            'created_by': None
        }
        entry = Blocklist(**entry_params)  # type: ignore[misc] # SQLAlchemy dynamic constructor

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

@blocklist_bp.route('/guardian/explain', methods=['POST'])
def explain_ip_impact():
    """Get detailed AI explanation about the impact of blocking an IP"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address', '').strip()
        
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        
        # Get detailed analysis from Guardian AI
        if GUARDIAN_AVAILABLE and guardian_enabled:
            import asyncio
            try:
                guard = get_guardian()
                if guard is None:
                    return jsonify({
                        'ip_address': ip_address,
                        'guardian_enabled': False,
                        'fallback_explanation': f'AI Guardian failed to initialize. Manual review recommended for {ip_address} before blocking.'
                    })
                
                # Run the async function in a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(guard.validate_blocklist_addition(ip_address))
                loop.close()
                
                return jsonify({
                    'ip_address': ip_address,
                    'risk_level': result['risk_level'],
                    'confidence': result['confidence'],
                    'detailed_explanation': result['recommendation'],
                    'reasons': result['reasons'],
                    'suggested_action': result['action'],
                    'analysis_time': result['analysis_time'],
                    'guardian_enabled': True
                })
            except Exception as e:
                print(f"Guardian analysis failed: {str(e)}")
                return jsonify({
                    'ip_address': ip_address,
                    'error': 'AI analysis failed',
                    'guardian_enabled': False,
                    'fallback_explanation': f'Unable to perform detailed analysis for {ip_address}. Consider consulting with network administrators before blocking this IP.'
                }), 500
        else:
            return jsonify({
                'ip_address': ip_address,
                'guardian_enabled': False,
                'fallback_explanation': f'AI Guardian is not available. Manual review recommended for {ip_address} before blocking.'
            })
            
    except Exception as e:
        print(f"Error in explain_ip_impact: {str(e)}")
        return jsonify({'error': 'Failed to analyze IP impact'}), 500