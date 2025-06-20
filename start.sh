#!/bin/bash
set -e  # Exit immediately if any command fails

echo "📂 Step 1: Creating database tables..."
cd db
python create_tables.py

echo "📁 Step 2: Generating and loading data..."
cd ../data
python datagen.py
python loadData.py

echo "🚀 Step 3: Starting Flask app..."
cd ..
flask run --port=8080