"""Template context processors."""
from flask import current_app, g, session
from datetime import datetime
from flask_wtf.csrf import generate_csrf as wtf_generate_csrf
from app.services.i18n import i18n_service

def _extract_nonce():
    """Return the script-src nonce provided by Talisman, if available."""
    nonce = getattr(g, 'csp_nonce', None)
    if isinstance(nonce, dict):
        nonce = nonce.get('script-src', '')
    if not nonce:
        return ''
    # Talisman provides header values like 'nonce-<value>'; attribute expects raw value
    if isinstance(nonce, str) and nonce.startswith('nonce-'):
        return nonce[len('nonce-'):]
    return nonce

def inject_template_vars():
    """Inject variables into all templates."""
    # Get current language
    current_language = session.get('language', 'en')
    
    # Define translation function
    def _(key, **kwargs):
        """Translation function for templates."""
        translation = i18n_service.translate(key, current_language)
        
        # Handle variable interpolation
        if kwargs:
            try:
                return translation.format(**kwargs)
            except (KeyError, ValueError):
                return translation
        
        return translation
    
    return {
        'csp_nonce': lambda: _extract_nonce(),
        # Use Flask-WTF CSRF token compatible with CSRFProtect
        'csrf_token': lambda: wtf_generate_csrf(),
        'app_name': current_app.config.get('APP_NAME', 'My Diary'),
        'current_year': lambda: datetime.utcnow().year,
        'debug': current_app.debug,
        'version': current_app.config.get('VERSION', '1.0.0'),
        'config': current_app.config,
        # i18n functions
        '_': _,
        'current_language': current_language,
        'available_languages': i18n_service.get_supported_locales(),
        'translate': i18n_service.translate,
    }
