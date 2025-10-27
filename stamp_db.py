#!/usr/bin/env python
"""Script to stamp the database with current migration state."""
from app import create_app, db
from flask_migrate import Migrate, stamp

def stamp_database():
    """Stamp the database with current migration state."""
    app = create_app()
    migrate = Migrate(app, db)

    with app.app_context():
        try:
            stamp()
            print("Database stamped successfully!")
            return True
        except Exception as e:
            print(f"Error stamping database: {str(e)}")
            return False

if __name__ == '__main__':
    stamp_database()
