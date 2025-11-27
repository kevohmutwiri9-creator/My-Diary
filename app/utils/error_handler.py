"""
Enhanced Error Handling System
Provides comprehensive error handling, logging, and user feedback
"""

import logging
import traceback
import sys
import os
from datetime import datetime
from functools import wraps
from flask import current_app, request, session, jsonify, render_template
from flask_login import current_user
from werkzeug.exceptions import HTTPException
from logging.handlers import RotatingFileHandler

class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize error handlers with Flask app"""
        app.errorhandler(Exception)(self.handle_exception)
        app.errorhandler(404)(self.handle_not_found)
        app.errorhandler(500)(self.handle_server_error)
        app.errorhandler(403)(self.handle_forbidden)
        app.errorhandler(429)(self.handle_rate_limit)
        app.errorhandler(413)(self.handle_payload_too_large)
        
        # Log configuration
        self.setup_logging(app)
    
    def setup_logging(self, app):
        """Setup enhanced logging with rotation."""
        # Ensure logs directory exists
        import os
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configure main app logger
        if not app.debug:
            # File logging with rotation
            log_file = os.path.join(logs_dir, 'my_diary.log')
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            # Error log file
            error_log_file = os.path.join(logs_dir, 'errors.log')
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=10240000,  # 10MB
                backupCount=5
            )
            error_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            error_handler.setLevel(logging.ERROR)
            app.logger.addHandler(error_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('My Diary startup')
    
    def log_error(self, error, context=None):
        """Enhanced error logging with context"""
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'request': {
                'method': request.method if request else None,
                'url': request.url if request else None,
                'user_agent': request.headers.get('User-Agent') if request else None,
                'ip': request.remote_addr if request else None,
            },
            'user': {
                'id': current_user.id if current_user.is_authenticated else None,
                'email': current_user.email if current_user.is_authenticated else None,
            } if current_user else None,
            'context': context or {}
        }
        
        # Log to application logger
        current_app.logger.error(f"Error occurred: {error_data}")
        
        # Store in session for debugging (in development)
        if current_app.debug:
            session['last_error'] = error_data
        
        return error_data
    
    def handle_exception(self, error):
        """Handle general exceptions"""
        error_data = self.log_error(error, {
            'handler': 'general_exception',
            'is_ajax': request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        })
        
        # AJAX requests get JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'An unexpected error occurred',
                'error_id': id(error_data),
                'debug_info': error_data if current_app.debug else None
            }), 500
        
        # Regular requests get error page
        return render_template('errors/500.html', 
                             error=error_data if current_app.debug else None), 500
    
    def handle_not_found(self, error):
        """Handle 404 errors"""
        error_data = self.log_error(error, {
            'handler': 'not_found',
            'requested_path': request.path
        })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'Page not found',
                'error_id': id(error_data)
            }), 404
        
        return render_template('errors/404.html'), 404
    
    def handle_server_error(self, error):
        """Handle 500 server errors"""
        error_data = self.log_error(error, {
            'handler': 'server_error'
        })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'error_id': id(error_data)
            }), 500
        
        return render_template('errors/500.html', 
                             error=error_data if current_app.debug else None), 500
    
    def handle_forbidden(self, error):
        """Handle 403 forbidden errors"""
        error_data = self.log_error(error, {
            'handler': 'forbidden',
            'required_permission': getattr(error, 'description', 'Unknown')
        })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'error_id': id(error_data)
            }), 403
        
        return render_template('errors/403.html'), 403
    
    def handle_rate_limit(self, error):
        """Handle 429 rate limit errors"""
        error_data = self.log_error(error, {
            'handler': 'rate_limit',
            'limit': getattr(error, 'description', 'Too many requests')
        })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded',
                'error_id': id(error_data),
                'retry_after': getattr(error, 'retry_after', 60)
            }), 429
        
        return render_template('errors/429.html', 
                             retry_after=getattr(error, 'retry_after', 60)), 429
    
    def handle_payload_too_large(self, error):
        """Handle 413 payload too large errors"""
        error_data = self.log_error(error, {
            'handler': 'payload_too_large',
            'content_length': request.content_length if request else None
        })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'File too large',
                'error_id': id(error_data)
            }), 413
        
        return render_template('errors/413.html'), 413

# Decorator for handling errors in specific functions
def handle_errors(fallback_message="An error occurred", log_error=True):
    """Decorator to handle errors in view functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    current_app.logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'error': fallback_message,
                        'error_type': type(e).__name__
                    }), 500
                
                # Flash message for regular requests
                from flask import flash
                flash(fallback_message, 'danger')
                
                # Try to redirect to safe location
                try:
                    from flask import redirect, url_for
                    return redirect(url_for('main.dashboard'))
                except:
                    return "An error occurred", 500
        
        return wrapper
    return decorator

# Service-level error handling
class ServiceError(Exception):
    """Base class for service errors"""
    def __init__(self, message, error_code=None, context=None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.utcnow()

class DatabaseError(ServiceError):
    """Database-related errors"""
    pass

class ValidationError(ServiceError):
    """Validation errors"""
    pass

class AuthenticationError(ServiceError):
    """Authentication errors"""
    pass

class AuthorizationError(ServiceError):
    """Authorization errors"""
    pass

class ExternalServiceError(ServiceError):
    """External service errors (API calls, etc.)"""
    pass

def safe_operation(operation_name=None, fallback_value=None, log_errors=True):
    """Decorator for safe operations with fallback"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ServiceError as e:
                if log_errors:
                    current_app.logger.error(f"Service error in {operation_name or func.__name__}: {e.message}")
                return fallback_value
            except Exception as e:
                if log_errors:
                    current_app.logger.error(f"Unexpected error in {operation_name or func.__name__}: {str(e)}", exc_info=True)
                return fallback_value
        return wrapper
    return decorator

# User-friendly error messages
ERROR_MESSAGES = {
    'database_connection': 'Unable to connect to the database. Please try again later.',
    'validation_failed': 'Please check your input and try again.',
    'authentication_required': 'You need to log in to access this feature.',
    'permission_denied': 'You don\'t have permission to perform this action.',
    'file_too_large': 'The file is too large. Please choose a smaller file.',
    'rate_limit_exceeded': 'Too many requests. Please wait a moment and try again.',
    'external_service_error': 'Unable to connect to external service. Please try again later.',
    'default': 'An unexpected error occurred. Please try again.'
}

def get_error_message(error_type):
    """Get user-friendly error message"""
    return ERROR_MESSAGES.get(error_type, ERROR_MESSAGES['default'])
