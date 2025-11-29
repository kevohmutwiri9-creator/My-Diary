#!/usr/bin/env python3
"""
Maintain user account during deployment
This script ensures your user account exists after each deployment
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User

def ensure_user_exists():
    """Ensure user account exists after deployment."""
    app = create_app()
    
    with app.app_context():
        # Your preferred login credentials
        email = "kevohmutwiri9@gmail.com"
        username = "kevohmu"
        password = "Admin123!"  # Change this to your preferred password
        
        print(f"🔧 Ensuring user exists: {email}")
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            print(f"✅ User '{existing_user.username}' already exists")
            print(f"   Email: {existing_user.email}")
            print(f"   ID: {existing_user.id}")
            print(f"   Created: {existing_user.created_at}")
            print(f"   Last login: {existing_user.last_login}")
            
            # Update password if needed (in case it was changed)
            existing_user.set_password(password)
            existing_user.is_active = True
            existing_user.is_verified = True
            existing_user.email_verified_at = datetime.utcnow()
            
            db.session.commit()
            print(f"🔄 Password updated for user: {email}")
            return existing_user
        
        # Create new user if doesn't exist
        try:
            user = User(
                username=username,
                email=email,
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.utcnow()
            )
            
            # Set password
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            print(f"✅ Successfully created user:")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   ID: {user.id}")
            print(f"   Created: {user.created_at}")
            print(f"   Password: {password}")
            
            return user
            
        except Exception as e:
            print(f"❌ Error creating user: {str(e)}")
            db.session.rollback()
            return None

def cleanup_test_users():
    """Remove test/admin users created during deployment."""
    app = create_app()
    
    with app.app_context():
        # Users to clean up (keep only your main account)
        cleanup_emails = [
            "admin@example.com",
            "kevohmutwiri35@gmail.com"
        ]
        
        for email in cleanup_emails:
            user = User.query.filter_by(email=email).first()
            if user:
                try:
                    # Delete user's entries first
                    from app.models.entry import Entry
                    Entry.query.filter_by(user_id=user.id).delete()
                    
                    # Delete the user
                    db.session.delete(user)
                    db.session.commit()
                    print(f"🗑️  Cleaned up test user: {email}")
                except Exception as e:
                    print(f"❌ Error cleaning up {email}: {str(e)}")
                    db.session.rollback()

if __name__ == '__main__':
    print("🔧 User Maintenance Script")
    print("=" * 40)
    
    # Ensure your main user exists
    ensure_user_exists()
    
    # Clean up test users
    cleanup_test_users()
    
    print("\n✅ User maintenance complete!")
    print("You can now login with:")
    print("   Email: kevohmutwiri9@gmail.com")
    print("   Password: Admin123!")
