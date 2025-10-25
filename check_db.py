import os
import sys
from app import create_app, db
from app.models import Entry, User

def check_database():
    app = create_app()
    with app.app_context():
        print("Checking database connection...")
        try:
            # Check if we can connect to the database
            db.engine.connect()
            print("✅ Successfully connected to the database.")
            
            # Check if the entries table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'entries' not in inspector.get_table_names():
                print("❌ 'entries' table does not exist!")
            else:
                print("✅ 'entries' table exists.")
                
                # Try to query the entries table
                try:
                    count = Entry.query.count()
                    print(f"✅ Successfully queried entries table. Found {count} entries.")
                except Exception as e:
                    print(f"❌ Error querying entries table: {str(e)}")
            
            # Check if the users table exists
            if 'users' not in inspector.get_table_names():
                print("❌ 'users' table does not exist!")
            else:
                print("✅ 'users' table exists.")
                
            # Print the database URL being used
            print(f"\nDatabase URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            print(f"Database path: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print("\nTroubleshooting steps:")
            print("1. Make sure the 'instance' directory exists and is writable")
            print("2. Check if the SQLite database file exists at the path above")
            print("3. Try deleting the database file and let the application create a new one")
            print("4. Check file permissions on the database file and its directory")

if __name__ == "__main__":
    check_database()
