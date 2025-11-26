"""
Analytics utilities for My Diary application
"""

from flask import current_app, request, g
from functools import wraps
import time


def track_page_view():
    """Track page view for analytics"""
    if current_app.config.get('GOOGLE_ANALYTICS_ID') and hasattr(g, 'can_use_analytics') and g.can_use_analytics:
        try:
            # This would be used with gtag.js on the frontend
            # Backend tracking can be implemented here if needed
            current_app.logger.info(f"Page view tracked: {request.path}")
        except Exception as e:
            current_app.logger.error(f"Analytics tracking error: {e}")


def track_event(category, action, label=None, value=None):
    """Track custom event for analytics"""
    if current_app.config.get('GOOGLE_ANALYTICS_ID') and hasattr(g, 'can_use_analytics') and g.can_use_analytics:
        try:
            # This would be used with gtag.js on the frontend
            current_app.logger.info(f"Event tracked: {category} - {action} - {label} - {value}")
        except Exception as e:
            current_app.logger.error(f"Analytics tracking error: {e}")


def track_user_action(action, details=None):
    """Track user-specific actions"""
    if current_app.config.get('GOOGLE_ANALYTICS_ID') and hasattr(g, 'can_use_analytics') and g.can_use_analytics:
        try:
            user_id = getattr(g, 'current_user', None)
            if user_id and user_id.is_authenticated:
                # Track user actions (without PII)
                track_event('user_action', action, label=str(user_id.id))
                current_app.logger.info(f"User action tracked: {action} by user {user_id.id}")
        except Exception as e:
            current_app.logger.error(f"User analytics tracking error: {e}")


def track_performance(timing_name, timing_value):
    """Track performance metrics"""
    if current_app.config.get('GOOGLE_ANALYTICS_ID') and hasattr(g, 'can_use_analytics') and g.can_use_analytics:
        try:
            track_event('performance', timing_name, value=timing_value)
        except Exception as e:
            current_app.logger.error(f"Performance tracking error: {e}")


def analytics_tracker(f):
    """Decorator to automatically track page views and performance"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Track page view
        track_page_view()
        
        # Execute the function
        result = f(*args, **kwargs)
        
        # Track performance
        end_time = time.time()
        timing_value = int((end_time - start_time) * 1000)  # Convert to milliseconds
        track_performance('page_load_time', timing_value)
        
        return result
    
    return decorated_function


def get_analytics_config():
    """Get analytics configuration for frontend"""
    config = {}
    
    if current_app.config.get('GOOGLE_ANALYTICS_ID'):
        config['google_analytics_id'] = current_app.config['GOOGLE_ANALYTICS_ID']
    
    if hasattr(g, 'can_use_analytics') and g.can_use_analytics:
        config['enabled'] = True
    else:
        config['enabled'] = False
    
    return config


# Custom event tracking functions
def track_entry_created(entry_type='diary'):
    """Track when user creates a new entry"""
    track_user_action('entry_created', {'type': entry_type})


def track_entry_updated(entry_type='diary'):
    """Track when user updates an entry"""
    track_user_action('entry_updated', {'type': entry_type})


def track_entry_deleted(entry_type='diary'):
    """Track when user deletes an entry"""
    track_user_action('entry_deleted', {'type': entry_type})


def track_user_login():
    """Track user login"""
    track_event('authentication', 'login')


def track_user_logout():
    """Track user logout"""
    track_event('authentication', 'logout')


def track_user_registration():
    """Track user registration"""
    track_event('authentication', 'registration')


def track_feature_usage(feature_name):
    """Track when user uses a specific feature"""
    track_user_action('feature_used', {'feature': feature_name})


def track_error(error_type, error_message=None):
    """Track application errors"""
    track_event('error', error_type, label=error_message)


def track_search(query, result_count=None):
    """Track search queries"""
    track_event('search', 'query', label=query, value=result_count)


def track_export(format_type, entry_count):
    """Track data exports"""
    track_event('data_export', format_type, value=entry_count)


def track_import(format_type, entry_count):
    """Track data imports"""
    track_event('data_import', format_type, value=entry_count)
