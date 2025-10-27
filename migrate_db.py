"""Script to handle database migrations."""
import os
from flask_migrate import Migrate, upgrade, migrate, init
from app import create_app
from app import db  # Import db directly from app module

def run_migrations():
    """Run database migrations."""
    # Create the application
    app = create_app()

    # Initialize Flask-Migrate with the app and db
    migrate_obj = Migrate()
    migrate_obj.init_app(app, db)

    with app.app_context():
        # Check if migrations directory exists, if not, initialize it
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        if not os.path.exists(migrations_dir):
            print("Initializing migrations directory...")
            init()

        try:
            # Create a new migration
            print("Creating migration...")
            migrate(message="Add security features and indexes")

            # Apply the migration
            print("Upgrading database...")
            upgrade()

            print("Database migration completed successfully!")
            return True

        except Exception as e:
            print(f"Error during migration: {str(e)}")
            print("Attempting to recover...")
            if hasattr(db, 'session') and db.session.is_active:
                db.session.rollback()
            print("Please check the error and try again.")
            return False

if __name__ == '__main__':
    run_migrations()