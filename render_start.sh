#!/bin/bash
# Render startup script for My Diary

echo "🚀 Starting My Diary application..."

# Set Flask environment
export FLASK_ENV=production

# Force SQLite as database for Render (to avoid SQL Server ODBC issues)
export DATABASE_URL="sqlite:///my_diary.db"

echo "📡 Using SQLite database: my_diary.db"

# Create database and tables before starting the app
python setup_sqlite.py

# Start the application with Gunicorn
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120
