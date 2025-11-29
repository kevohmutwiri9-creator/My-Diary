#!/usr/bin/env python3
"""
Create admin user in production database
Run this script on Render to create your user account
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User

def create_admin_user():
    """Create admin user if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email='kevohmutwiri9@gmail.com').first()
        
        if existing_user:
            print(f"✅ User '{existing_user.username}' already exists in database")
            print(f"   Email: {existing_user.email}")
            print(f"   ID: {existing_user.id}")
            print(f"   Created: {existing_user.created_at}")
            return existing_user
        
        # Create new user
        try:
            user = User(
                username='kevohmu',
                email='kevohmutwiri9@gmail.com',
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.utcnow()
            )
            
            # Set password (use a strong password that you'll remember)
            # IMPORTANT: Change this to your actual password!
            user.set_password('YourSecurePassword123!')  # <-- CHANGE THIS
            
            db.session.add(user)
            db.session.commit()
            
            print(f"✅ Successfully created user:")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   ID: {user.id}")
            print(f"   Created: {user.created_at}")
            print(f"\n⚠️  IMPORTANT: Remember to change the password in production!")
            print(f"   Current password: 'YourSecurePassword123!'")
            print(f"   Update this in the script and run again, or change via profile settings.")
            
            return user
            
        except Exception as e:
            print(f"❌ Error creating user: {str(e)}")
            db.session.rollback()
            return None

def list_all_users():
    """List all users in the database."""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("📭 No users found in database")
            return
        
        print(f"👥 Found {len(users)} user(s) in database:")
        print("-" * 60)
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Active: {user.is_active}")
            print(f"Verified: {user.is_verified}")
            print(f"Created: {user.created_at}")
            print("-" * 60)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        list_all_users()
    else:
        print("🔧 Creating production user...")
        create_admin_user()
