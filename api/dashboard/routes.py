from flask import Blueprint, render_template, jsonify, request
from flask_cors import cross_origin
from models import Blocklist, Safelist, Historical
from datetime import datetime, timedelta
from sqlalchemy import and_

dashboard_bp = Blueprint(
    'dashboard',
    __name__,
    template_folder='../../frontend/templates',
    static_folder='../../frontend/static'
)

@dashboard_bp.route('/')
@cross_origin()
def root():
    return render_template('dashboard.html')

@dashboard_bp.route('/data')
@cross_origin()
def get_dashboard_data():
    try:
        print("=== Starting Dashboard Data Retrieval ===")
        
        total_blocked = Blocklist.query.count()
        total_safelist = Safelist.query.count()
        historical_count = Historical.query.count()
        
        print(f"Database Counts:")
        print(f"- Blocklist: {total_blocked}")
        print(f"- Safelist: {total_safelist}")
        print(f"- Historical: {historical_count}")

        # Get historical records for data processing
        historical_records = Historical.query.all()
        blocklist_records = Blocklist.query.all()
        
        print(f"Retrieved {len(historical_records)} historical records")
        print(f"Retrieved {len(blocklist_records)} blocklist records")

        # Combine all records for peak analysis without pandas
        all_records = []
        
        # Process historical records
        for r in historical_records:
            all_records.append({
                'added_at': r.added_at,
                'unblocked_at': r.unblocked_at,
                'ip_address': str(r.ip_address),
                'created_by': str(r.created_by) if r.created_by else 'Unknown',
                'source': 'historical'
            })
        
        # Process blocklist records
        for r in blocklist_records:
            all_records.append({
                'added_at': r.added_at,
                'unblocked_at': r.expires_at,
                'ip_address': str(r.ip_address),
                'created_by': str(r.created_by) if r.created_by else 'Unknown',
                'source': 'blocklist'
            })

        print(f"Combined {len(all_records)} total records for analysis")

        # Calculate peak activity hour (this week) without pandas
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        
        weekly_hours = []
        for record in all_records:
            if record['added_at'] and record['added_at'] >= week_ago:
                weekly_hours.append(record['added_at'].hour)
        
        if weekly_hours:
            # Count frequency of each hour
            hour_counts = {}
            for hour in weekly_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            # Find peak hour
            peak_hour = max(hour_counts.keys(), key=lambda h: hour_counts[h])
            peak_hour_formatted = f"{peak_hour:02d}:00"
        else:
            peak_hour_formatted = "N/A"

        # Calculate peak activity day (this month) without pandas
        month_ago = now - timedelta(days=30)
        
        weekly_days = []
        for record in all_records:
            if record['added_at'] and record['added_at'] >= month_ago:
                day_name = record['added_at'].strftime('%A')
                weekly_days.append(day_name)
        
        if weekly_days:
            # Count frequency of each day
            day_counts = {}
            for day in weekly_days:
                day_counts[day] = day_counts.get(day, 0) + 1
            
            # Find peak day
            peak_day = max(day_counts.keys(), key=lambda d: day_counts[d])
        else:
            peak_day = "N/A"

        stats = {
            'total_blocked': total_blocked,
            'total_safelist': total_safelist,
            'peak_hour': peak_hour_formatted,
            'peak_day': peak_day
        }
        
        print("Calculated stats:", stats)

        # Calculate blocks by creator
        creator_counts = {}
        for record in historical_records:
            creator = str(record.created_by) if record.created_by else 'Unknown'
            creator_counts[creator] = creator_counts.get(creator, 0) + 1

        # Calculate timeline data (group by date)
        timeline_counts = {}
        for record in historical_records:
            if record.added_at:
                date_str = record.added_at.strftime('%Y-%m-%d')
                timeline_counts[date_str] = timeline_counts.get(date_str, 0) + 1

        # Calculate IP distribution
        ipv4_count = 0
        ipv6_count = 0
        for record in historical_records:
            ip_str = str(record.ip_address)
            if '.' in ip_str and ':' not in ip_str:  # Simple IPv4 check
                ipv4_count += 1
            else:
                ipv6_count += 1

        # Get recent activity (last 5 records)
        recent_records = sorted(historical_records, key=lambda r: r.added_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:5]
        recent_activity = []
        for record in recent_records:
            if record.added_at:
                recent_activity.append({
                    'added_at': record.added_at.isoformat(),
                    'ip_address': str(record.ip_address),
                    'created_by': str(record.created_by) if record.created_by else 'Unknown'
                })

        response_data = {
            'stats': stats,
            'blocks_by_creator': creator_counts,
            'timeline_data': timeline_counts,
            'ip_distribution': {'ipv4': ipv4_count, 'ipv6': ipv6_count},
            'recent_activity': recent_activity
        }
        
        print("Final response data:", response_data)
        return jsonify(response_data)

    except Exception as e:
        print(f"Error in get_dashboard_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/filter_stats')
@cross_origin()
def filter_stats():
    stat_type = request.args.get("type")  # blocklist or safelist
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    if not (stat_type and from_date and to_date):
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        # Add 23:59:59 to include the entire end date
        to_dt = to_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        return jsonify({"error": "Invalid date format (expected YYYY-MM-DD)"}), 400

    model_map = {
        "blocklist": (Blocklist, "added_at"),
        "safelist": (Safelist, "added_at")
    }

    if stat_type not in model_map:
        return jsonify({"error": "Invalid stat type"}), 400

    model, field_name = model_map[stat_type]
    field = getattr(model, field_name)

    try:
        count = model.query.filter(field >= from_dt, field <= to_dt).count()
        return jsonify({"count": count, "type": stat_type})
    except Exception as e:
        return jsonify({"error": str(e)}), 500