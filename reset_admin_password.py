#!/usr/bin/env python3
"""
Quick script to reset admin password
"""

import os
import sys
from sqlalchemy import create_engine, text

def reset_admin_password():
    """Reset admin password directly"""
    
    # Get database URL from environment
    database_url = os.environ.get(
        'DATABASE_URL',
        'mssql+pyodbc:///?odbc_connect=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=MyDiaryDB;Trusted_Connection=yes;'
    )
    
    print("🔑 Resetting admin password...")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION"))
            version = result.fetchone()[0]
            print(f"✅ Connected to SQL Server: {version.split('\\n')[0]}")
        
        # Import app and reset password
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import create_app, db
        from config_production import ProductionConfig
        
        app = create_app(ProductionConfig)
        
        with app.app_context():
            from app.models import User
            
            # Find admin user
            admin_user = User.query.filter_by(email='admin@example.com').first()
            
            if admin_user:
                print(f"👤 Found admin user: {admin_user.username} (ID: {admin_user.id})")
                admin_user.set_password('Admin123!')
                db.session.commit()
                print("✅ Admin password reset successfully!")
                print("📧 Email: admin@example.com")
                print("🔑 Password: Admin123!")
            else:
                print("❌ Admin user not found. Creating new admin user...")
                admin_user = User(
                    email='admin@example.com',
                    username='admin2',  # Use different username
                    is_admin=True
                )
                admin_user.set_password('Admin123!')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ New admin user created!")
                print("📧 Email: admin@example.com")
                print("🔑 Password: Admin123!")
                print("👤 Username: admin2")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    reset_admin_password()
