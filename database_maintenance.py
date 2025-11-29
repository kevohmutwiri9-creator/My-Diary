#!/usr/bin/env python3
"""
Database maintenance for deployment
This script ensures database integrity and preserves all users
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User

def ensure_admin_user():
    """Ensure admin user exists (only for admin access)."""
    app = create_app()
    
    with app.app_context():
        # Your admin credentials
        email = "kevohmutwiri9@gmail.com"
        username = "kevohmu"
        password = "kevoh2071M@6309"
        
        print(f"🔧 Ensuring admin user exists: {email}")
        
        # Check if admin user already exists
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            print(f"✅ Admin user '{existing_user.username}' already exists")
            # Update password if needed
            existing_user.set_password(password)
            existing_user.is_active = True
            db.session.commit()
            print(f"🔄 Admin password updated")
        else:
            # Create admin user if doesn't exist
            try:
                user = User(
                    username=username,
                    email=email
                )
                
                user.set_password(password)
                user.is_active = True
                
                db.session.add(user)
                db.session.commit()
                
                print(f"✅ Admin user created:")
                print(f"   Username: {user.username}")
                print(f"   Email: {user.email}")
                print(f"   ID: {user.id}")
                
            except Exception as e:
                print(f"❌ Error creating admin user: {str(e)}")
                db.session.rollback()

def ensure_biko_user():
    """Ensure bikoafrikana@gmail.com user exists."""
    app = create_app()
    
    with app.app_context():
        # Biko user credentials
        email = "bikoafrikana@gmail.com"
        username = "bikoafrikana"
        password = "User123!"  # Default password
        
        print(f"🔧 Ensuring biko user exists: {email}")
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            print(f"✅ Biko user '{existing_user.username}' already exists")
            # Update password if needed
            existing_user.set_password(password)
            existing_user.is_active = True
            db.session.commit()
            print(f"🔄 Biko user password updated")
        else:
            # Create user if doesn't exist
            try:
                user = User(
                    username=username,
                    email=email
                )
                
                user.set_password(password)
                user.is_active = True
                
                db.session.add(user)
                db.session.commit()
                
                print(f"✅ Biko user created:")
                print(f"   Username: {user.username}")
                print(f"   Email: {user.email}")
                print(f"   Password: {password}")
                print(f"   ID: {user.id}")
                
            except Exception as e:
                print(f"❌ Error creating biko user: {str(e)}")
                db.session.rollback()

def preserve_all_users():
    """Ensure all existing users remain active and verified."""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        print(f"\n👥 Preserving {len(users)} existing users...")
        
        for user in users:
            # Ensure all users are active and verified
            user.is_active = True
            user.is_verified = True
            if not user.email_verified_at:
                user.email_verified_at = datetime.utcnow()
        
        db.session.commit()
        print(f"✅ All {len(users)} users preserved and activated")

def database_health_check():
    """Check database health and report status."""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 Database Health Check")
        print("=" * 40)
        
        try:
            # Test database connection
            db.engine.execute("SELECT 1")
            print("✅ Database connection: OK")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        # Count users
        user_count = User.query.count()
        print(f"👥 Total users: {user_count}")
        
        # Show recent users
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        print(f"\n📋 Recent users:")
        for user in recent_users:
            status = "✅ Active" if user.is_active else "❌ Inactive"
            verified = "✅ Verified" if user.is_verified else "❌ Not verified"
            print(f"   {user.email} - {status} - {verified} - Created: {user.created_at}")
        
        if user_count > 5:
            print(f"   ... and {user_count - 5} more users")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "health":
            database_health_check()
        elif command == "admin":
            ensure_admin_user()
        elif command == "biko":
            ensure_biko_user()
        elif command == "preserve":
            preserve_all_users()
        else:
            print("Usage:")
            print("  python database_maintenance.py health    # Check database health")
            print("  python database_maintenance.py admin     # Ensure admin user")
            print("  python database_maintenance.py biko      # Ensure biko user")
            print("  python database_maintenance.py preserve  # Preserve all users")
    else:
        # Default: full maintenance
        print("🔧 Database Maintenance Started")
        print("=" * 40)
        
        ensure_admin_user()
        ensure_biko_user()
        preserve_all_users()
        database_health_check()
        
        print(f"\n✅ Database maintenance complete!")
        print(f"\n📝 Notes:")
        print(f"   - Admin user: kevohmutwiri9@gmail.com")
        print(f"   - Biko user: bikoafrikana@gmail.com (password: User123!)")
        print(f"   - All existing users preserved")
        print(f"   - New users can register normally")
        print(f"   - Database ready for production")
