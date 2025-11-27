"""
Production configuration for My Diary application.
"""

import os
from datetime import timedelta


class ProductionConfig:
    """Production configuration settings."""
    
    # Basic Flask settings
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///my_diary.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
        'echo': False,
    }
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Password policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBER = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Password reset
    PASSWORD_RESET_TOKEN_MAX_AGE = int(os.environ.get('PASSWORD_RESET_TOKEN_MAX_AGE', 3600))
    PASSWORD_RESET_SALT = os.environ.get('PASSWORD_RESET_SALT', 'password-reset-salt')
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() in ['true', 'on', '1']
    
    # Analytics and monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID')
    
    # Cache settings
    CACHE_TYPE = 'redis' if os.environ.get('REDIS_URL') else 'simple'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Content Security Policy
    CSP_DEFAULT_SRC = "'self'"
    CSP_SCRIPT_SRC = "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://www.google-analytics.com"
    CSP_STYLE_SRC = "'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    CSP_IMG_SRC = "'self' data: https:"
    CSP_FONT_SRC = "'self' https://cdn.jsdelivr.net"
    CSP_CONNECT_SRC = "'self'"
    
    # Performance optimizations
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
    TEMPLATES_AUTO_RELOAD = False
    
    # API settings
    API_RATE_LIMIT = "1000 per day"
    API_TIMEOUT = 30
    
    # Feature flags
    ENABLE_COMMUNITY_FEATURES = os.environ.get('ENABLE_COMMUNITY_FEATURES', 'true').lower() in ['true', 'on', '1']
    ENABLE_ANALYTICS = os.environ.get('ENABLE_ANALYTICS', 'true').lower() in ['true', 'on', '1']
    ENABLE_AI_ASSISTANT = os.environ.get('ENABLE_AI_ASSISTANT', 'false').lower() in ['true', 'on', '1']
    
    @staticmethod
    def init_app(app):
        """Initialize production app."""
        import logging
        
        # Configure logging
        if not app.debug and not app.testing:
            if ProductionConfig.LOG_TO_STDOUT:
                stream_handler = logging.StreamHandler()
                stream_handler.setLevel(logging.INFO)
                app.logger.addHandler(stream_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('My Diary production startup')
        
        # Initialize Sentry if DSN is provided
        if ProductionConfig.SENTRY_DSN:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
            sentry_sdk.init(
                dsn=ProductionConfig.SENTRY_DSN,
                integrations=[
                    FlaskIntegration(),
                    SqlalchemyIntegration(),
                ],
                traces_sample_rate=0.1,
                environment='production'
            )
        
        # Initialize cache
        if ProductionConfig.CACHE_REDIS_URL:
            try:
                import redis
                app.redis = redis.from_url(ProductionConfig.CACHE_REDIS_URL)
                app.logger.info('Redis cache connected')
            except Exception as e:
                app.logger.warning(f'Redis connection failed: {e}')
                app.redis = None
