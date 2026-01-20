#!/usr/bin/env python3
"""
Database initialization script for My Diary
Run this script to create database tables
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Entry

def init_db():
    """Initialize database tables"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Creating database tables...")
            
            # Create all tables
            db.create_all()
            
            print("Database tables created successfully!")
            print("Tables created:")
            print("- User")
            print("- Entry")
            
        except Exception as e:
            print(f"Error creating database tables: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = init_db()
    if success:
        print("Database initialization completed successfully!")
    else:
        print("Database initialization failed!")
        sys.exit(1)
