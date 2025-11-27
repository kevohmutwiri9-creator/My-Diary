#!/bin/bash
# Render startup script for My Diary

echo "🚀 Starting My Diary application..."

# Set Flask environment
export FLASK_ENV=production

# Check if DATABASE_URL is set, if not use SQLite as fallback
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️ DATABASE_URL not set, using SQLite fallback"
    export DATABASE_URL="sqlite:///my_diary.db"
fi

echo "📡 Database URL: ${DATABASE_URL:0:50}..."

# Start the application with Gunicorn
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120
