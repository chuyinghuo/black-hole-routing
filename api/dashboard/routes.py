import pandas as pd
import numpy as np
from flask import Blueprint, render_template, jsonify
from flask_cors import cross_origin
from pathlib import Path

DATA_FILE = 'db/data/bhr_data.csv'
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
        # Load the CSV file
        df = pd.read_csv(DATA_FILE)
        print(f"Successfully loaded CSV from {DATA_FILE}")
        
        # Convert date strings to datetime objects first
        df['added'] = pd.to_datetime(df['added_at'])
        df['unblock_at'] = pd.to_datetime(df['unblocked_at'])
        
        # Calculate duration in hours
        df['duration'] = (df['unblock_at'] - df['added']).dt.total_seconds() / 3600
        
        # Convert numpy types to native Python types
        stats = {
            'total_blocked': int(len(df)),
            'unique_sources': int(df['created_by'].nunique()),
            'avg_duration': float(round(df['duration'].mean(), 2)),
            'expiring_soon': int(len(df[df['unblock_at'] >= pd.Timestamp.now()]))
        }
        
        # Convert blocks_by_creator counts to int
        blocks_by_creator = df['created_by'].value_counts().astype(int).to_dict()
        
        # Get timeline data using the converted 'added' column
        timeline_data = df.groupby(df['added'].dt.date.astype(str)).size().astype(int).to_dict()
        
        # Get IP version distribution
        ipv4_count = int(df['ip_address'].str.contains(r'\d+\.\d+\.\d+\.\d+').sum())
        ipv6_count = int(len(df) - ipv4_count)
        
        # Format recent activity data
        recent_activity = df.sort_values('added', ascending=False).head(5)[
            ['added_at', 'ip_address', 'created_by']
        ].to_dict('records')
        
        response_data = {
            'stats': stats,
            'blocks_by_creator': blocks_by_creator,
            'timeline_data': timeline_data,
            'ip_distribution': {'ipv4': ipv4_count, 'ipv6': ipv6_count},
            'recent_activity': recent_activity
        }
        
        print("Processed data successfully")
        print(f"Stats: {stats}")
        print(f"Timeline data: {timeline_data}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        print(f"Error occurred at line: {e.__traceback__.tb_lineno}")
        return jsonify({'error': str(e)}), 500