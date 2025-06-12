import pandas as pd
import numpy as np
from flask import Blueprint, render_template, jsonify
from flask_cors import cross_origin
from models import Blocklist, Safelist, Historical
from datetime import datetime

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
        
        # Get stats from respective tables
        total_blocked = Blocklist.query.count()
        total_safelist = Safelist.query.count()
        historical_count = Historical.query.count()
        
        print(f"Database Counts:")
        print(f"- Blocklist: {total_blocked}")
        print(f"- Safelist: {total_safelist}")
        print(f"- Historical: {historical_count}")

        # Load Historical data
        records = Historical.query.all()
        print(f"Retrieved {len(records)} historical records")

        # Create DataFrame
        df = pd.DataFrame([{
            'added_at': r.added_at,
            'unblocked_at': r.unblocked_at,
            'ip_address': r.ip_address,
            'created_by': r.created_by
        } for r in records])
        
        print(f"DataFrame created with {len(df)} rows")
        print("DataFrame head:")
        print(df.head())

        # Convert date strings to datetime objects - with UTC handling
        df['added'] = pd.to_datetime(df['added_at'], utc=True)
        df['unblock_at'] = pd.to_datetime(df['unblocked_at'], utc=True)

        # Calculate duration in hours
        df['duration'] = (df['unblock_at'] - df['added']).dt.total_seconds() / 3600

        # Stats box
        stats = {
            'total_blocked': total_blocked,
            'total_safelist': total_safelist,
            'avg_duration': float(round(df['duration'].mean(), 2)) if not df['duration'].empty else 0,
            'expiring_soon': int(len(df[df['unblock_at'] >= pd.Timestamp.now(tz='UTC')])),
        }
        
        print("Calculated stats:", stats)

        # Blocks by creator
        blocks_by_creator = df['created_by'].value_counts().astype(int).to_dict()

        # Timeline - Convert to date string after handling timezone
        timeline_data = df.groupby(df['added'].dt.date.astype(str)).size().astype(int).to_dict()

        # IP type detection
        ipv4_count = int(df['ip_address'].str.contains(r'\d+\.\d+\.\d+\.\d+').sum())
        ipv6_count = int(len(df) - ipv4_count)

        # Recent activity - Convert datetime to string for JSON serialization
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