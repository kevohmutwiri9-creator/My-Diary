#!/usr/bin/env python3
"""
Check database status and users
Run this to debug login issues
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.entry import Entry

def check_database():
    """Check database status and contents."""
    app = create_app()
    
    with app.app_context():
        print("🔍 Database Health Check")
        print("=" * 50)
        
        # Check database connection
        try:
            db.engine.execute("SELECT 1")
            print("✅ Database connection: OK")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        # Check tables
        try:
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Database tables: {len(tables)} found")
            for table in tables:
                print(f"   - {table}")
        except Exception as e:
            print(f"❌ Error checking tables: {e}")
        
        print("\n👥 Users Check")
        print("-" * 30)
        
        users = User.query.all()
        print(f"Total users: {len(users)}")
        
        for user in users:
            print(f"\n📧 User: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   ID: {user.id}")
            print(f"   Active: {user.is_active}")
            print(f"   Verified: {user.is_verified}")
            print(f"   Created: {user.created_at}")
            print(f"   Has password hash: {'Yes' if user.password_hash else 'No'}")
            print(f"   Password hash length: {len(user.password_hash) if user.password_hash else 0}")
        
        print("\n📝 Entries Check")
        print("-" * 30)
        
        entries = Entry.query.all()
        print(f"Total entries: {len(entries)}")
        
        for entry in entries[:5]:  # Show first 5 entries
            print(f"\n📄 Entry: {entry.title or 'Untitled'}")
            print(f"   ID: {entry.id}")
            print(f"   User ID: {entry.user_id}")
            print(f"   Created: {entry.created_at}")
            print(f"   Content length: {len(entry.content) if entry.content else 0}")
        
        if len(entries) > 5:
            print(f"\n... and {len(entries) - 5} more entries")
        
        print("\n🔑 Login Test")
        print("-" * 30)
        
        test_email = "kevohmutwiri9@gmail.com"
        user = User.query.filter_by(email=test_email).first()
        
        if user:
            print(f"✅ User found: {test_email}")
            print(f"   Username: {user.username}")
            print(f"   Account locked: {'Yes' if user.account_locked_until else 'No'}")
            if user.account_locked_until:
                print(f"   Locked until: {user.account_locked_until}")
        else:
            print(f"❌ User NOT found: {test_email}")
            print("   This user needs to be created in the database!")

if __name__ == '__main__':
    check_database()
