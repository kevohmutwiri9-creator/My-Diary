"""Security-related utility functions."""
import re
from datetime import datetime, timedelta
from flask import current_app, request
from flask_limiter import RateLimitExceeded

def is_strong_password(password):
    """Check if the password meets strength requirements."""
    if len(password) < current_app.config.get('PASSWORD_MIN_LENGTH', 12):
        return False, 'Password must be at least 12 characters long'
    
    if current_app.config.get('PASSWORD_REQUIRE_UPPERCASE', True) and not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'
        
    if current_app.config.get('PASSWORD_REQUIRE_LOWERCASE', True) and not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'
        
    if current_app.config.get('PASSWORD_REQUIRE_NUMBER', True) and not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one number'
        
    if current_app.config.get('PASSWORD_REQUIRE_SPECIAL', True) and not re.search(r'[^A-Za-z0-9]', password):
        return False, 'Password must contain at least one special character'
    
    return True, ''

def check_rate_limit():
    """Check if the current request exceeds rate limits."""
    try:
        # This will raise RateLimitExceeded if limit is exceeded
        current_app.limiter.check()
        return True, ''
    except RateLimitExceeded as e:
        return False, f'Rate limit exceeded. Please try again in {e.retry_after} seconds'

def get_client_ip():
    """Get the client's IP address."""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    return request.remote_addr

def generate_csrf_token():
    """Generate a CSRF token for forms."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = os.urandom(24).hex()
    return session['_csrf_token']

def is_valid_csrf_token(token):
    """Validate a CSRF token."""
    if '_csrf_token' not in session:
        return False
    return token == session['_csrf_token']
