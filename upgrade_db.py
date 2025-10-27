#!/usr/bin/env python
"""Script to upgrade the database directly."""
from app import create_app, db
from flask_migrate import Migrate, upgrade

def upgrade_database():
    """Upgrade the database to the latest migration."""
    app = create_app()
    migrate = Migrate(app, db)

    with app.app_context():
        try:
            upgrade()
            print("Database upgraded successfully!")
            return True
        except Exception as e:
            print(f"Error upgrading database: {str(e)}")
            if hasattr(db, 'session') and db.session.is_active:
                db.session.rollback()
            return False

if __name__ == '__main__':
    upgrade_database()
