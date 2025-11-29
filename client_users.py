#!/usr/bin/env python3
"""
Client user management for smooth interaction
This script manages multiple client accounts for deployment
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User

# Client accounts configuration
CLIENT_USERS = [
    {
        "email": "kevohmutwiri9@gmail.com",
        "username": "kevohmu",
        "password": "kevoh2071M@6309",
        "role": "admin"
    },
    # Add your clients here
    {
        "email": "client1@example.com", 
        "username": "client1",
        "password": "Client123!",
        "role": "client"
    },
    {
        "email": "client2@example.com",
        "username": "client2", 
        "password": "Client456!",
        "role": "client"
    },
    # Add more clients as needed
]

def ensure_client_users():
    """Ensure all client users exist after deployment."""
    app = create_app()
    
    with app.app_context():
        print(f"👥 Managing {len(CLIENT_USERS)} user accounts...")
        
        for user_config in CLIENT_USERS:
            email = user_config["email"]
            username = user_config["username"]
            password = user_config["password"]
            role = user_config.get("role", "client")
            
            print(f"\n🔧 Processing user: {email}")
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            
            if existing_user:
                print(f"✅ User '{existing_user.username}' already exists")
                
                # Update password if needed
                existing_user.set_password(password)
                existing_user.is_active = True
                existing_user.is_verified = True
                existing_user.email_verified_at = datetime.utcnow()
                
                db.session.commit()
                print(f"🔄 Password updated for: {email}")
            else:
                # Create new user
                try:
                    user = User(
                        username=username,
                        email=email,
                        is_active=True,
                        is_verified=True,
                        email_verified_at=datetime.utcnow()
                    )
                    
                    user.set_password(password)
                    
                    db.session.add(user)
                    db.session.commit()
                    
                    print(f"✅ Created new user:")
                    print(f"   Username: {user.username}")
                    print(f"   Email: {user.email}")
                    print(f"   Role: {role}")
                    print(f"   Password: {password}")
                    
                except Exception as e:
                    print(f"❌ Error creating user {email}: {str(e)}")
                    db.session.rollback()

def list_all_users():
    """List all users in the database."""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        print(f"\n👥 Total users in database: {len(users)}")
        print("-" * 60)
        
        for user in users:
            print(f"📧 {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Active: {user.is_active}")
            print(f"   Verified: {user.is_verified}")
            print(f"   Created: {user.created_at}")
            print("-" * 60)

def create_user_interactive():
    """Interactive user creation for adding new clients."""
    app = create_app()
    
    with app.app_context():
        print("\n👤 Create New Client User")
        print("=" * 40)
        
        email = input("Enter email: ").strip()
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()
        
        if not email or not username or not password:
            print("❌ All fields are required!")
            return
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            return
        
        try:
            user = User(
                username=username,
                email=email,
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.utcnow()
            )
            
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            print(f"\n✅ User created successfully!")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Can login with password: {password}")
            
        except Exception as e:
            print(f"❌ Error creating user: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            list_all_users()
        elif command == "create":
            create_user_interactive()
        elif command == "maintain":
            ensure_client_users()
        else:
            print("Usage:")
            print("  python client_users.py maintain  # Ensure all users exist")
            print("  python client_users.py list     # List all users")
            print("  python client_users.py create    # Create new user")
    else:
        # Default: maintain all users
        ensure_client_users()
        
        print(f"\n✅ User management complete!")
        print(f"\n📋 Client Login Credentials:")
        for user_config in CLIENT_USERS:
            print(f"   {user_config['email']} / {user_config['password']}")
