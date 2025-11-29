"""
Security Enhancement System
Provides comprehensive security measures and protection
"""

import time
import hashlib
import re
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import current_app, request, session, redirect, url_for, flash, jsonify
from flask_login import current_user
from werkzeug.security import generate_password_hash
import bleach
import secrets

class SecurityEnhancer:
    """Enhanced security protection system"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security features"""
        # Security headers
        @app.after_request
        def add_security_headers(response):
            # Content Security Policy
            if not app.debug:
                csp = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'; "
                    "form-action 'self'"
                )
                response.headers['Content-Security-Policy'] = csp
            
            # Other security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
            
            return response
        
        # Log security events
        self.setup_security_logging(app)
    
    def setup_security_logging(self, app):
        """Setup security-specific logging"""
        # Ensure logs directory exists
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        security_logger = logging.getLogger('security')
        
        if not security_logger.handlers:
            handler = logging.FileHandler(os.path.join(logs_dir, 'security.log'))
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
            ))
            security_logger.addHandler(handler)
            security_logger.setLevel(logging.INFO)
        
        app.security_logger = security_logger
    
    def log_security_event(self, event_type, details, severity='INFO'):
        """Log security events"""
        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'severity': severity
        }
        
        current_app.security_logger.info(f"Security Event: {event_data}")
        
        # Log critical events to main logger
        if severity in ['CRITICAL', 'HIGH']:
            current_app.logger.warning(f"Critical Security Event: {event_type} - {details}")

# Password Security
class PasswordSecurity:
    """Enhanced password security"""
    
    @staticmethod
    def validate_password_strength(password, user_data=None):
        """Validate password strength with comprehensive checks"""
        errors = []
        
        # Length requirements
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        elif len(password) > 128:
            errors.append("Password must be less than 128 characters long")
        
        # Character requirements
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Common patterns
        common_patterns = [
            r'123456', r'password', r'qwerty', r'admin', r'letmein',
            r'welcome', r'monkey', r'dragon', r'master', r'sunshine'
        ]
        
        for pattern in common_patterns:
            if pattern.lower() in password.lower():
                errors.append(f"Password contains common pattern: {pattern}")
                break
        
        # Check against user data if provided
        if user_data:
            if user_data.get('email') and user_data['email'].split('@')[0].lower() in password.lower():
                errors.append("Password cannot contain your email username")
            
            if user_data.get('username') and user_data['username'].lower() in password.lower():
                errors.append("Password cannot contain your username")
        
        return {
            'is_strong': len(errors) == 0,
            'errors': errors,
            'strength_score': PasswordSecurity.calculate_strength_score(password)
        }
    
    @staticmethod
    def calculate_strength_score(password):
        """Calculate password strength score (0-100)"""
        score = 0
        
        # Length contribution
        score += min(len(password) * 2, 40)  # Max 40 points for length
        
        # Character variety
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15
        
        # Complexity bonus
        unique_chars = len(set(password))
        if unique_chars > len(password) * 0.5:
            score += 15
        
        return min(score, 100)

# Input Validation and Sanitization
class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def sanitize_html(content, allowed_tags=None, allowed_attributes=None):
        """Sanitize HTML content"""
        if allowed_tags is None:
            allowed_tags = {
                'p', 'br', 'strong', 'em', 'u', 'i', 'b',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
                'a', 'img'
            }
        
        if allowed_attributes is None:
            allowed_attributes = {
                'a': ['href', 'title'],
                'img': ['src', 'alt', 'title', 'width', 'height'],
                '*': ['class']
            }
        
        return bleach.clean(
            content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if len(username) < 3 or len(username) > 30:
            return False
        
        # Only allow alphanumeric, underscore, and hyphen
        pattern = r'^[a-zA-Z0-9_-]+$'
        return re.match(pattern, username) is not None
    
    @staticmethod
    def sanitize_filename(filename):
        """Sanitize filename for security"""
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename.strip()

# Rate Limiting
class RateLimiter:
    """Enhanced rate limiting"""
    
    def __init__(self):
        self.attempts = {}
    
    def is_allowed(self, key, limit, window=3600):
        """Check if action is allowed"""
        now = time.time()
        
        if key not in self.attempts:
            self.attempts[key] = []
        
        # Clean old attempts
        self.attempts[key] = [attempt for attempt in self.attempts[key] if now - attempt < window]
        
        # Check limit
        if len(self.attempts[key]) >= limit:
            return False
        
        # Record attempt
        self.attempts[key].append(now)
        return True
    
    def get_remaining_attempts(self, key, limit, window=3600):
        """Get remaining attempts"""
        now = time.time()
        
        if key not in self.attempts:
            return limit
        
        recent_attempts = [attempt for attempt in self.attempts[key] if now - attempt < window]
        return max(0, limit - len(recent_attempts))

# Session Security
class SessionSecurity:
    """Enhanced session security"""
    
    @staticmethod
    def generate_secure_token():
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_session_integrity():
        """Validate session integrity"""
        if 'csrf_token' not in session:
            return False
        
        # Check session age
        session_age = time.time() - session.get('created_at', 0)
        if session_age > 86400:  # 24 hours
            session.clear()
            return False
        
        # Check IP consistency (optional, can be disabled for mobile users)
        if current_app.config.get('SESSION_IP_CHECK', False):
            current_ip = request.remote_addr
            stored_ip = session.get('ip_address')
            if stored_ip and current_ip != stored_ip:
                session.clear()
                return False
        
        return True
    
    @staticmethod
    def refresh_session():
        """Refresh session security"""
        session.permanent = True
        session['last_activity'] = time.time()
        session['csrf_token'] = SessionSecurity.generate_secure_token()

# Decorators
def require_csrf_token(f):
    """Require CSRF token for sensitive operations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = session.get('csrf_token')
            form_token = request.form.get('csrf_token')
            header_token = request.headers.get('X-CSRF-Token')
            
            submitted_token = form_token or header_token
            
            if not token or not submitted_token or not hmac.compare_digest(token, submitted_token):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': 'Invalid CSRF token'}), 403
                abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(limit=100, window=3600, key_func=None):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if key_func:
                key = key_func()
            else:
                key = f"{request.remote_addr}:{request.endpoint}"
            
            limiter = RateLimiter()
            
            if not limiter.is_allowed(key, limit, window):
                remaining = limiter.get_remaining_attempts(key, limit, window)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False, 
                        'error': 'Rate limit exceeded',
                        'remaining': remaining,
                        'reset_time': time.time() + window
                    }), 429
                
                abort(429)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_input(validation_rules):
    """Input validation decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Only validate on POST/PUT requests to avoid redirect loops on GET requests
            if request.method not in ['POST', 'PUT']:
                return f(*args, **kwargs)
                
            errors = {}
            
            for field, rules in validation_rules.items():
                value = request.form.get(field) or request.json.get(field) if request.is_json else request.form.get(field)
                
                # Required validation
                if rules.get('required', False) and not value:
                    errors[field] = f"{field} is required"
                    continue
                
                if value is not None:
                    # Type validation
                    if 'type' in rules:
                        if rules['type'] == 'email' and not InputValidator.validate_email(value):
                            errors[field] = f"{field} must be a valid email"
                        elif rules['type'] == 'username' and not InputValidator.validate_username(value):
                            errors[field] = f"{field} contains invalid characters"
                    
                    # Length validation
                    if 'min_length' in rules and len(value) < rules['min_length']:
                        errors[field] = f"{field} must be at least {rules['min_length']} characters"
                    
                    if 'max_length' in rules and len(value) > rules['max_length']:
                        errors[field] = f"{field} must be no more than {rules['max_length']} characters"
            
            if errors:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'errors': errors}), 400
                else:
                    from flask import flash
                    for field, error in errors.items():
                        flash(error, 'danger')
                    return redirect(request.referrer or url_for('main.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Security monitoring
class SecurityMonitor:
    """Security monitoring and anomaly detection"""
    
    def __init__(self, app=None):
        self.app = app
        self.suspicious_activities = {}
    
    def detect_brute_force(self, ip_address, username=None):
        """Detect brute force attempts"""
        key = f"login_attempts:{ip_address}"
        if username:
            key += f":{username}"
        
        limiter = RateLimiter()
        
        # More than 5 failed attempts in 15 minutes is suspicious
        if not limiter.is_allowed(key, 5, 900):
            self.log_suspicious_activity('brute_force', {
                'ip': ip_address,
                'username': username,
                'attempts': len(limiter.attempts.get(key, []))
            })
            return True
        
        return False
    
    def detect_mass_registration(self, ip_address):
        """Detect mass registration attempts"""
        key = f"registration:{ip_address}"
        limiter = RateLimiter()
        
        # More than 3 registrations in 10 minutes is suspicious
        if not limiter.is_allowed(key, 3, 600):
            self.log_suspicious_activity('mass_registration', {
                'ip': ip_address,
                'attempts': len(limiter.attempts.get(key, []))
            })
            return True
        
        return False
    
    def log_suspicious_activity(self, activity_type, details):
        """Log suspicious activity"""
        if hasattr(current_app, 'security_logger'):
            current_app.security_logger.warning(f"Suspicious Activity: {activity_type} - {details}")
        
        # Store for monitoring
        if activity_type not in self.suspicious_activities:
            self.suspicious_activities[activity_type] = []
        
        self.suspicious_activities[activity_type].append({
            'timestamp': datetime.utcnow(),
            'details': details
        })

# Initialize security enhancer
security_enhancer = SecurityEnhancer()
