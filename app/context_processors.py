"""Template context processors."""
from flask import current_app
from .utils.csrf import get_csrf_token

def inject_template_vars():
    """Inject variables into all templates."""
    return {
        'csp_nonce': lambda: current_app.config.get('CSP_NONCE', ''),
        'csrf_token': get_csrf_token,
        'app_name': current_app.config.get('APP_NAME', 'My Diary'),
        'current_year': lambda: datetime.utcnow().year,
        'debug': current_app.debug,
        'version': current_app.config.get('VERSION', '1.0.0')
    }
