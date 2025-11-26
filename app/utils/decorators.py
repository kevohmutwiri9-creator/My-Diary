"""Custom decorators for the application."""

from functools import wraps
from flask import flash, redirect, url_for, abort, session, request
from flask_login import current_user


def admin_required(f):
    """Decorator to ensure user is logged in and has admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin:
            flash('Admin access required for this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        # Check 2FA verification for admin users
        if current_user.two_factor_enabled:
            # Import here to avoid circular import
            from app.routes.two_factor import check_2fa_verification
            if not check_2fa_verification():
                session['2fa_next'] = request.url if request.url else url_for('main.dashboard')
                flash('Two-factor authentication is required for admin access.', 'info')
                return redirect(url_for('two_factor.verify'))
        
        return f(*args, **kwargs)
    return decorated_function


def admin_or_404(f):
    """Decorator that returns 404 if user is not admin (instead of redirecting)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(404)
        return f(*args, **kwargs)
    return decorated_function
