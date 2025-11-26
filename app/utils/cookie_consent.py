"""Cookie consent management for GDPR compliance."""

from flask import session, request, current_app
from datetime import datetime, timedelta
import json

class CookieConsent:
    """Manages cookie consent and preferences."""
    
    CONSENT_COOKIE_NAME = 'cookie_consent'
    PREFERENCES_COOKIE_NAME = 'cookie_preferences'
    
    # Cookie categories
    CATEGORIES = {
        'necessary': {
            'name': 'Essential Cookies',
            'description': 'These cookies are essential for the website to function properly.',
            'required': True,
            'cookies': ['session', 'remember_me', 'csrf_token']
        },
        'analytics': {
            'name': 'Analytics Cookies',
            'description': 'Help us understand how visitors interact with our website.',
            'required': False,
            'cookies': ['_ga', '_gid', '_gat']
        },
        'marketing': {
            'name': 'Marketing Cookies',
            'description': 'Used to deliver advertisements that are relevant to you.',
            'required': False,
            'cookies': ['ads', 'ad_storage', 'ad_user_data']
        },
        'personalization': {
            'name': 'Personalization Cookies',
            'description': 'Allow us to remember your preferences and settings.',
            'required': False,
            'cookies': ['theme', 'language', 'timezone']
        }
    }
    
    @classmethod
    def has_consent(cls):
        """Check if user has given cookie consent."""
        # Always return True to disable cookie consent banner
        return True
    
    @classmethod
    def get_consent_date(cls):
        """Get the date when consent was given."""
        return session.get('cookie_consent_date')
    
    @classmethod
    def get_preferences(cls):
        """Get user's cookie preferences."""
        preferences = session.get(cls.PREFERENCES_COOKIE_NAME, {})
        
        # Always include necessary cookies
        preferences['necessary'] = True
        
        return preferences
    
    @classmethod
    def set_consent(cls, preferences):
        """Save user's cookie consent preferences."""
        session[cls.CONSENT_COOKIE_NAME] = True
        session['cookie_consent_date'] = datetime.utcnow().isoformat()
        session[cls.PREFERENCES_COOKIE_NAME] = preferences
        session.permanent = True
    
    @classmethod
    def can_use_category(cls, category):
        """Check if we can use cookies from a specific category."""
        if not cls.has_consent():
            return cls.CATEGORIES.get(category, {}).get('required', False)
        
        preferences = cls.get_preferences()
        return preferences.get(category, cls.CATEGORIES.get(category, {}).get('required', False))
    
    @classmethod
    def can_use_analytics(cls):
        """Check if analytics cookies are allowed."""
        return cls.can_use_category('analytics')
    
    @classmethod
    def can_use_marketing(cls):
        """Check if marketing cookies are allowed."""
        return cls.can_use_category('marketing')
    
    @classmethod
    def can_use_personalization(cls):
        """Check if personalization cookies are allowed."""
        return cls.can_use_category('personalization')
    
    @classmethod
    def withdraw_consent(cls):
        """Withdraw cookie consent (GDPR right)."""
        session.pop(cls.CONSENT_COOKIE_NAME, None)
        session.pop(cls.PREFERENCES_COOKIE_NAME, None)
        session.pop('cookie_consent_date', None)
    
    @classmethod
    def get_consent_data(cls):
        """Get all consent data for export (GDPR)."""
        return {
            'consent_given': cls.has_consent(),
            'consent_date': cls.get_consent_date(),
            'preferences': cls.get_preferences(),
            'ip_address': request.environ.get('REMOTE_ADDR'),
            'user_agent': request.headers.get('User-Agent'),
            'categories': cls.CATEGORIES
        }
    
    @classmethod
    def update_preferences(cls, preferences):
        """Update existing cookie preferences."""
        if cls.has_consent():
            session[cls.PREFERENCES_COOKIE_NAME] = preferences
            session['cookie_consent_date'] = datetime.utcnow().isoformat()
            return True
        return False

def init_cookie_consent(app):
    """Initialize cookie consent system."""
    
    @app.before_request
    def check_cookie_consent():
        """Check cookie consent before each request."""
        # Don't check consent for static files or consent-related routes
        if (request.endpoint and 
            (request.endpoint.startswith('static') or 
             request.endpoint in ['main.cookie_consent', 'main.save_cookie_consent'])):
            return
        
        # Set default preferences if no consent exists
        if not CookieConsent.has_consent():
            # Only allow necessary cookies by default
            session[CookieConsent.PREFERENCES_COOKIE_NAME] = {
                'necessary': True,
                'analytics': False,
                'marketing': False,
                'personalization': False
            }
    
    return app
