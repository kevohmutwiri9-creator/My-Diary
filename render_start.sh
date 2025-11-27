#!/bin/bash
# Render startup script for My Diary

echo "🚀 Starting My Diary application..."

# Set Flask environment
export FLASK_ENV=production

# Start the application with Gunicorn
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120
