"""Security middleware for adding security headers to responses."""
from flask import request, current_app
from functools import wraps

def add_security_headers(response):
    """Add security headers to all responses."""
    # Don't add headers for static files in development
    if request.path.startswith('/static/'):
        return response
    
    # Security Headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HSTS - Enable in production only
    if current_app.config.get('ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # CSP - Report-Only mode can be enabled for testing
    if current_app.config.get('CSP_REPORT_ONLY'):
        response.headers['Content-Security-Policy-Report-Only'] = \
            "default-src 'self'; " \
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://pagead2.googlesyndication.com; " \
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; " \
            "img-src 'self' data: https:; " \
            "font-src 'self' https://cdn.jsdelivr.net; " \
            "frame-src https://www.google.com; " \
            "report-uri /csp-report-endpoint/;"
    else:
        response.headers['Content-Security-Policy'] = \
            "default-src 'self'; " \
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://pagead2.googlesyndication.com; " \
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; " \
            "img-src 'self' data: https:; " \
            "font-src 'self' https://cdn.jsdelivr.net; " \
            "frame-src https://www.google.com;"
    
    # Feature Policy (now Permissions Policy)
    response.headers['Permissions-Policy'] = \
        "geolocation=(), microphone=(), camera=(), payment=()"
    
    return response

def ssl_required(fn):
    ""
    Decorator to require SSL for specific routes.
    Use with @ssl_required above the route.
    """
    @wraps(fn)
    def decorated_view(*args, **kwargs):
        if current_app.config.get('ENV') == 'production':
            if not request.is_secure:
                from flask import redirect, request
                return redirect(request.url.replace('http://', 'https://', 1), code=301)
        return fn(*args, **kwargs)
    return decorated_view
