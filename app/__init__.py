import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
migrate = Migrate()

def create_app(config_class=Config):
    """Application factory function to create and configure the Flask app."""
    # Configure logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Use a different log file for each process
    import socket
    hostname = socket.gethostname()
    log_file = f'logs/my_diary_{hostname}.log'
    
    # Use a FileHandler instead of RotatingFileHandler to avoid permission issues
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # Create and configure the app
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(__name__, template_folder=template_dir)
    app.config.from_object(config_class)

    # Configure logging
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    # Remove the default Flask handler that writes to stderr
    # This prevents duplicate log messages in the console
    app.logger.handlers = [h for h in app.logger.handlers if not isinstance(h, logging.StreamHandler) or h != console_handler]
    
    app.logger.info('My Diary startup')

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.utils.filters import markdown_to_html
    
    # Register template filter
    app.jinja_env.filters['markdown_to_html'] = markdown_to_html
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

# Import models after db initialization to avoid circular imports
from app.models import user, entry, template