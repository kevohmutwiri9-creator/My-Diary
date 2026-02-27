import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Set SECRET_KEY from environment first
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
    
    # Handle DATABASE_URL for production (PostgreSQL) vs development (SQLite)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        print(f"Using production database: {database_url[:50]}...")
    else:
        # Fallback to SQLite for local development
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
        print("Using development database: SQLite")
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"

    # Import User model after app initialization
    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Register error handlers
    def register_error_handlers(app):
        from flask import render_template
        
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('404.html'), 404

        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            return render_template('500.html'), 500

        @app.errorhandler(403)
        def forbidden_error(error):
            return render_template('404.html'), 403

    register_error_handlers(app)

    # Create database tables within app context
    with app.app_context():
        try:
            # Import models to ensure they're registered
            from . import models
            from .models import User, Entry
            
            # Create all tables
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {e}")

    return app
