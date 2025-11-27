#!/usr/bin/env python3
"""
SQL Server Setup Script for My Diary
This script helps set up the database for SQL Server
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def setup_sql_server_database():
    """Set up SQL Server database and create tables"""
    
    # Get database URL from environment or use default
    database_url = os.environ.get(
        'DATABASE_URL',
        'mssql+pyodbc:///?odbc_connect=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=MyDiaryDB;Trusted_Connection=yes;'
    )
    
    print("🗄️ Setting up SQL Server database...")
    print(f"📡 Database URL: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION"))
            version = result.fetchone()[0]
            print(f"✅ Connected to SQL Server: {version.split('\\n')[0]}")
        
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
            
            if admin_user:
                print("👤 Admin user already exists, resetting password...")
                admin_user.set_password('Admin123!')  # Reset to 8 characters
                db.session.commit()
                print("✅ Admin password reset (email: admin@example.com, password: Admin123!)")
            else:
                print("👤 Creating default admin user...")
                admin_user = User(
                    email='admin@example.com',
                    username='admin',
                    is_admin=True
                )
                admin_user.set_password('Admin123!')  # 8 characters with special chars
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin user created (email: admin@example.com, password: Admin123!)")
            
            print("🎉 SQL Server database setup complete!")
            
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure SQL Server is running")
        print("2. Check that ODBC Driver 17 for SQL Server is installed")
        print("3. Verify the database name and server address")
        print("4. Ensure Windows Authentication is enabled if using Trusted_Connection")
        print("5. Try using the curly braces format: Driver={ODBC Driver 17 for SQL Server}")
        return False
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False
    
    return True

def test_connection():
    """Test database connection without creating tables"""
    database_url = os.environ.get(
        'DATABASE_URL',
        'mssql+pyodbc:///?odbc_connect=Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=MyDiaryDB;Trusted_Connection=yes;'
    )
    
    print("🔍 Testing SQL Server connection...")
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            if test_value == 1:
                print("✅ Database connection successful!")
                return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Try these solutions:")
        print("1. Use curly braces: Driver={ODBC Driver 17 for SQL Server}")
        print("2. Install ODBC Driver 17 for SQL Server")
        print("3. Check SQL Server is running")
        print("4. Verify database name exists")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='SQL Server setup for My Diary')
    parser.add_argument('--test-only', action='store_true', help='Only test database connection')
    args = parser.parse_args()
    
    if args.test_only:
        test_connection()
    else:
        setup_sql_server_database()
