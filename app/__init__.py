# In app/__init__.py
import os
import logging
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

# Import custom filters
from app.utils.filters import markdown_to_html

# Initialize extensions without app
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()
talisman = Talisman()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.refresh_view = 'auth.login'
login_manager.needs_refresh_message = "Session timed out, please re-login to continue."
mail = Mail()

def create_app(config_class=Config):
    """Application factory function."""
    # Point to static and template folders at project root
    import os
    # Get the absolute path to the project root directory
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    static_path = os.path.join(basedir, 'static')
    
    # Create Flask app with explicit paths
    app = Flask(__name__, 
                static_folder=static_path,
                static_url_path='/static',
                template_folder='templates')
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    csrf.init_app(app)
    # Configure Content Security Policy for production to allow required CDNs
    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            'https://cdn.jsdelivr.net',
            'https://pagead2.googlesyndication.com',
            'https://googleads.g.doubleclick.net'
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            'https://cdn.jsdelivr.net'
        ],
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'", 'https://cdn.jsdelivr.net'],
        'frame-src': ['https://www.google.com', 'https://googleads.g.doubleclick.net'],
        'connect-src': [
            "'self'",
            'https://pagead2.googlesyndication.com',
            'https://googleads.g.doubleclick.net',
            'https://cdn.jsdelivr.net'
        ]
    }
    talisman.init_app(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src']
    )
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Initialize rate limiter
    def get_identifier():
        from flask import request
        from flask_login import current_user
        if current_user.is_authenticated:
            return f"user:{current_user.id}"
        return f"ip:{get_remote_address()}"
    
    limiter = Limiter(
        app=app,
        key_func=get_identifier,
        default_limits=app.config.get('RATELIMIT_DEFAULT', ['200 per day', '50 per hour']),
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
        enabled=app.config.get('RATELIMIT_ENABLED', False)  # Disable in development
    )
    app.limiter = limiter  # Make limiter available on app instance

    # Configure logging
    if not os.path.exists('logs'):
        os.makedirs('logs', exist_ok=True)

    # Use a different log file for each process
    import socket
    hostname = socket.gethostname()
    log_file = f'logs/my_diary_{hostname}.log'

    # Configure file handler without rotation to avoid permission issues
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)

    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # Configure logging
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Remove any existing handlers to prevent duplicate logs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    app.logger.info('Application startup')
    app.logger.info('My Diary startup')

    # Import models here to avoid circular imports (but after db is initialized)
    from app import models

    # Register custom Jinja filters (before blueprints)
    app.jinja_env.filters['markdown_to_html'] = markdown_to_html

    # Register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.assistant import assistant_bp
    app.register_blueprint(assistant_bp, url_prefix='/assistant')

    from app.context_processors import inject_template_vars
    app.context_processor(inject_template_vars)

    # Configure Gemini API key
    app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

    # Create tables
    with app.app_context():
        db.create_all()

    return app

# This import must be at the bottom to avoid circular imports
from app import models