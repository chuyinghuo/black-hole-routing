import pandas as pd
import numpy as np
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

        # Combine Historical and Blocklist data for peak activity calculations
        historical_records = Historical.query.all()
        blocklist_records = Blocklist.query.all()
        
        # Convert to DataFrame format
        all_records = []
        
        # Add Historical records
        for r in historical_records:
            all_records.append({
                'added_at': r.added_at,
                'unblocked_at': r.unblocked_at,
                'ip_address': r.ip_address,
                'created_by': r.created_by,
                'source': 'historical'
            })
        
        # Add Blocklist records (avoid duplicates by checking IP + date combination)
        for r in blocklist_records:
            # Check if this IP with same added_at already exists in historical
            duplicate = any(
                hr['ip_address'] == r.ip_address and 
                hr['added_at'] == r.added_at 
                for hr in all_records
            )
            if not duplicate:
                all_records.append({
                    'added_at': r.added_at,
                    'unblocked_at': r.expires_at,  # Use expires_at for blocklist
                    'ip_address': r.ip_address,
                    'created_by': r.created_by,
                    'source': 'blocklist'
                })

        records = historical_records  # Keep original for other calculations
        print(f"Retrieved {len(records)} historical records")
        print(f"Combined {len(all_records)} total records for peak analysis")

        df = pd.DataFrame([{
            'added_at': r.added_at,
            'unblocked_at': r.unblocked_at,
            'ip_address': r.ip_address,
            'created_by': r.created_by
        } for r in records])
        
        # Create combined DataFrame for peak calculations
        combined_df = pd.DataFrame(all_records)
        
        print(f"DataFrame created with {len(df)} rows")
        print("DataFrame head:")
        print(df.head())

        df['added'] = pd.to_datetime(df['added_at'], utc=True)
        df['unblock_at'] = pd.to_datetime(df['unblocked_at'], utc=True)
        df['duration'] = (df['unblock_at'] - df['added']).dt.total_seconds() / 3600

        # Calculate peak activity hour (weekly) using combined data
        now = pd.Timestamp.now(tz='UTC')
        week_ago = now - pd.Timedelta(days=7)
        
        if not combined_df.empty:
            combined_df['added'] = pd.to_datetime(combined_df['added_at'], utc=True)
            weekly_data = combined_df[combined_df['added'] >= week_ago]
            
            if not weekly_data.empty:
                weekly_data['hour'] = weekly_data['added'].dt.hour
                hourly_activity = weekly_data['hour'].value_counts()
                peak_hour = hourly_activity.index[0] if not hourly_activity.empty else 0
                peak_hour_formatted = f"{peak_hour:02d}:00"
                print(f"Peak hour this week: {peak_hour_formatted} (from {len(weekly_data)} records)")
            else:
                peak_hour_formatted = "N/A"
                print("No records in the last 7 days")
        else:
            peak_hour_formatted = "N/A"
            print("No combined data available")

        # Calculate peak activity day (monthly) using combined data
        month_ago = now - pd.Timedelta(days=30)
        
        if not combined_df.empty:
            monthly_data = combined_df[combined_df['added'] >= month_ago]
            
            if not monthly_data.empty:
                monthly_data['day_of_week'] = monthly_data['added'].dt.day_name()
                daily_activity = monthly_data['day_of_week'].value_counts()
                peak_day = daily_activity.index[0] if not daily_activity.empty else "N/A"
                print(f"Peak day this month: {peak_day} (from {len(monthly_data)} records)")
            else:
                peak_day = "N/A"
                print("No records in the last 30 days")
        else:
            peak_day = "N/A"
            print("No combined data available")

        stats = {
            'total_blocked': total_blocked,
            'total_safelist': total_safelist,
            'peak_hour': peak_hour_formatted,
            'peak_day': peak_day
        }
        
        print("Calculated stats:", stats)

        blocks_by_creator = df['created_by'].value_counts().astype(int).to_dict()
        timeline_data = df.groupby(df['added'].dt.date.astype(str)).size().astype(int).to_dict()
        ipv4_count = int(df['ip_address'].str.contains(r'\d+\.\d+\.\d+\.\d+').sum())
        ipv6_count = int(len(df) - ipv4_count)

        recent_activity = df.sort_values('added', ascending=False).head(5)
        recent_activity = [{
            'added_at': row['added_at'].isoformat(),
            'ip_address': row['ip_address'],
            'created_by': row['created_by']
        } for _, row in recent_activity.iterrows()]

        response_data = {
            'stats': stats,
            'blocks_by_creator': blocks_by_creator,
            'timeline_data': timeline_data,
            'ip_distribution': {'ipv4': ipv4_count, 'ipv6': ipv6_count},
            'recent_activity': recent_activity
        }
        
        print("Final response data:", response_data)
        return jsonify(response_data)

    except Exception as e:
        print(f"Error in get_dashboard_data: {str(e)}")
        print(f"Error occurred at line: {e.__traceback__.tb_lineno}")
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