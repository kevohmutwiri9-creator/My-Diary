from flask_compress import Compress
from flask_talisman import Talisman

def init_performance(app):
    # Enable Gzip compression
    Compress(app)
    
    # Security headers and CSP
    csp = {
        'default-src': "'self'",
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://code.jquery.com"],
        'img-src': ["'self'", "data:", "https:"],
        'font-src': ["'self'", "https://cdnjs.cloudflare.com", "https://fonts.gstatic.com"],
        'connect-src': ["'self'"]
    }
    
    Talisman(
        app,
        force_https=True,
        strict_transport_security=True,
        session_cookie_secure=True,
        content_security_policy=csp
    )
