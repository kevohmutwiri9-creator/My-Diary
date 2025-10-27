"""CSRF protection utilities."""
import os
import hmac
import hashlib
from datetime import datetime, timedelta
from flask import session, current_app, request, abort

def generate_csrf_token():
    """Generate a CSRF token and store it in the session."""
    if '_csrf_token' not in session:
        # Generate a new token
        token = os.urandom(32).hex()
        session['_csrf_token'] = token
        session['_csrf_timestamp'] = datetime.utcnow().timestamp()
    return session['_csrf_token']

def validate_csrf_token(token):
    """Validate a CSRF token."""
    if not token or token != session.get('_csrf_token'):
        current_app.logger.warning('CSRF token validation failed: Invalid token')
        return False
    
    # Check if token has expired (30 minutes)
    token_timestamp = session.get('_csrf_timestamp')
    if not token_timestamp:
        current_app.logger.warning('CSRF token validation failed: No timestamp')
        return False
        
    token_age = datetime.utcnow() - datetime.fromtimestamp(token_timestamp)
    if token_age > timedelta(minutes=30):
        current_app.logger.warning('CSRF token validation failed: Token expired')
        return False
    
    return True

def csrf_protect(f):
    """Decorator to protect routes with CSRF validation."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            token = request.form.get('_csrf_token') or request.headers.get('X-CSRFToken')
            
            if not token or not validate_csrf_token(token):
                current_app.logger.error(f'CSRF validation failed for {request.endpoint}')
                abort(403, 'CSRF token is invalid or has expired')
                
        return f(*args, **kwargs)
    
    return decorated_function

def get_csrf_token():
    """Get the current CSRF token, generating one if needed."""
    return generate_csrf_token()
