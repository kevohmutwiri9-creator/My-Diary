"""Template context processors."""
from flask import current_app
from datetime import datetime
from flask_wtf.csrf import generate_csrf as wtf_generate_csrf

def inject_template_vars():
    """Inject variables into all templates."""
    return {
        'csp_nonce': lambda: current_app.config.get('CSP_NONCE', ''),
        # Use Flask-WTF CSRF token compatible with CSRFProtect
        'csrf_token': lambda: wtf_generate_csrf(),
        'app_name': current_app.config.get('APP_NAME', 'My Diary'),
        'current_year': lambda: datetime.utcnow().year,
        'debug': current_app.debug,
        'version': current_app.config.get('VERSION', '1.0.0'),
        'config': current_app.config
    }
