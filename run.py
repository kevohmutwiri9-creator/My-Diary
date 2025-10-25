#!/usr/bin/env python3
"""
Simple development server for My Diary application.
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting My Diary...")
    print("📖 Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop")
    app.run(debug=True, host='0.0.0.0', port=5000)
