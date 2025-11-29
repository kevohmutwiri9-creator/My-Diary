#!/usr/bin/env python3
"""
Diagnose user accounts in production database
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User

def check_all_users():
    """Check all users in the database."""
    app = create_app()
    
    with app.app_context():
        print("Diagnosing User Accounts")
        print("=" * 50)
        
        # Get all users
        users = User.query.all()
        
        print(f"Total users in database: {len(users)}")
        print("-" * 50)
        
        for user in users:
            print(f"User: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   ID: {user.id}")
            print(f"   Active: {user.is_active}")
            print(f"   Admin: {user.is_admin}")
            print(f"   Created: {user.created_at}")
            print("-" * 50)
        
        # Check specific user
        target_email = "bikoafrikana@gmail.com"
        target_user = User.query.filter_by(email=target_email).first()
        
        print(f"\nChecking specific user: {target_email}")
        if target_user:
            print(f"User found:")
            print(f"   Username: {target_user.username}")
            print(f"   ID: {target_user.id}")
            print(f"   Active: {target_user.is_active}")
            print(f"   Admin: {target_user.is_admin}")
            print(f"   Created: {target_user.created_at}")
        else:
            print(f"User NOT found in database!")
            print(f"   This user needs to be recreated")
        
        return users, target_user

def create_missing_user():
    """Create the missing user account."""
    app = create_app()
    
    with app.app_context():
        target_email = "bikoafrikana@gmail.com"
        
        # Check if user exists
        existing_user = User.query.filter_by(email=target_email).first()
        if existing_user:
            print(f"User {target_email} already exists")
            return existing_user
        
        # Create user with default password
        try:
            user = User(
                username="bikoafrikana",
                email=target_email,
                email_verified_at=datetime.utcnow()
            )
            
            # Set default password - they can change it later
            user.set_password("User123!")
            user.is_active = True
            
            db.session.add(user)
            db.session.commit()
            
            print(f"Created missing user:")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Password: User123!")
            print(f"   ID: {user.id}")
            print(f"   Created: {user.created_at}")
            
            return user
            
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            db.session.rollback()
            return None

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "create":
        create_missing_user()
    else:
        check_all_users()
        
        print(f"\nTo create missing user:")
        print(f"   python diagnose_users.py create")
        print(f"\nDefault password will be: User123!")
        print(f"   User should change this after login")
