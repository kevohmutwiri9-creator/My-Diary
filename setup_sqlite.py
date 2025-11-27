#!/usr/bin/env python3
"""
SQLite Setup Script for My Diary (Fallback)
This script sets up the database for SQLite deployment
"""

import os
import sys
from sqlalchemy import create_engine, text

def setup_sqlite_database():
    """Set up SQLite database and create tables"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///my_diary.db')
    
    print("🗄️ Setting up SQLite database...")
    print(f"📡 Database URL: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT sqlite_version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to SQLite: version {version}")
        
        # Import app and create tables
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app import create_app, db
        from config_production import ProductionConfig
        
        app = create_app(ProductionConfig)
        
        with app.app_context():
            print("🏗️ Creating database tables...")
            
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Check if admin user exists
            from app.models import User
            admin_user = User.query.filter_by(email='admin@example.com').first()
            
            if not admin_user:
                print("👤 Creating default admin user...")
                admin_user = User(
                    email='admin@example.com',
                    username='admin',
                    is_admin=True
                )
                admin_user.set_password('Admin123!')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin user created (email: admin@example.com, password: Admin123!)")
            else:
                print("👤 Admin user already exists")
            
            # Check if kevoh user exists
            kevoh_user = User.query.filter_by(email='kevohmutwiri35@gmail.com').first()
            
            if not kevoh_user:
                print("👤 Creating kevoh admin user...")
                kevoh_user = User(
                    email='kevohmutwiri35@gmail.com',
                    username='kevoh',
                    is_admin=True
                )
                kevoh_user.set_password('Admin123!')
                db.session.add(kevoh_user)
                db.session.commit()
                print("✅ Kevoh admin user created (email: kevohmutwiri35@gmail.com, password: Admin123!)")
            else:
                print("👤 Kevoh user already exists")
            
            print("🎉 SQLite database setup complete!")
            
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    setup_sqlite_database()
