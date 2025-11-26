"""Two-Factor Authentication routes."""

from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from app import db
from app.services.two_factor_service import (
    enable_2fa_for_user, confirm_2fa_setup, disable_2fa_for_user,
    verify_backup_code, regenerate_backup_codes, verify_2fa_token,
    create_2fa_session, clear_2fa_session
)
from app.utils.decorators import admin_required
import logging

logger = logging.getLogger(__name__)

two_factor_bp = Blueprint('two_factor', __name__, url_prefix='/2fa')


@two_factor_bp.route('/setup')
@login_required
@admin_required
def setup():
    """Setup 2FA for admin user."""
    if current_user.two_factor_enabled:
        flash('2FA is already enabled for your account.', 'info')
        return redirect(url_for('two_factor.manage'))
    
    # Generate 2FA setup data
    setup_data = enable_2fa_for_user(current_user)
    
    return render_template('two_factor/setup.html', **setup_data)


@two_factor_bp.route('/enable', methods=['POST'])
@login_required
@admin_required
def enable():
    """Enable 2FA after verification."""
    verification_token = request.form.get('verification_token')
    
    if not verification_token:
        flash('Verification code is required.', 'danger')
        return redirect(url_for('two_factor.setup'))
    
    success, message = confirm_2fa_setup(current_user, verification_token)
    
    if success:
        flash(message, 'success')
        return redirect(url_for('two_factor.manage'))
    else:
        flash(message, 'danger')
        return redirect(url_for('two_factor.setup'))


@two_factor_bp.route('/disable', methods=['POST'])
@login_required
@admin_required
def disable():
    """Disable 2FA for admin user."""
    password = request.form.get('password')
    
    if not password:
        flash('Password is required to disable 2FA.', 'danger')
        return redirect(url_for('two_factor.manage'))
    
    success, message = disable_2fa_for_user(current_user, password)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('two_factor.manage'))


@two_factor_bp.route('/manage')
@login_required
@admin_required
def manage():
    """Manage 2FA settings."""
    if not current_user.two_factor_enabled:
        flash('2FA is not enabled for your account.', 'info')
        return redirect(url_for('two_factor.setup'))
    
    return render_template('two_factor/manage.html')


@two_factor_bp.route('/verify', methods=['GET', 'POST'])
@login_required
def verify():
    """Verify 2FA token for login."""
    if not current_user.two_factor_enabled:
        return redirect(url_for('main.dashboard'))
    
    # Check if this is from login flow
    if request.method == 'POST':
        token = request.form.get('token')
        backup_code = request.form.get('backup_code')
        
        if token:
            # Verify TOTP token
            if verify_2fa_token(current_user, token):
                # Create 2FA session
                session_token = create_2fa_session(current_user)
                session['2fa_verified'] = True
                session['2fa_session_token'] = session_token
                
                # Redirect to intended page
                next_page = session.get('2fa_next', url_for('main.dashboard'))
                session.pop('2fa_next', None)
                
                flash('Successfully authenticated with 2FA.', 'success')
                return redirect(next_page)
            else:
                flash('Invalid authentication code.', 'danger')
        
        elif backup_code:
            # Verify backup code
            if verify_backup_code(current_user, backup_code):
                # Create 2FA session
                session_token = create_2fa_session(current_user)
                session['2fa_verified'] = True
                session['2fa_session_token'] = session_token
                
                flash('Successfully authenticated with backup code. Consider regenerating your backup codes.', 'warning')
                
                next_page = session.get('2fa_next', url_for('main.dashboard'))
                session.pop('2fa_next', None)
                
                return redirect(next_page)
            else:
                flash('Invalid backup code.', 'danger')
        
        else:
            flash('Please provide an authentication code or backup code.', 'danger')
    
    return render_template('two_factor/verify.html')


@two_factor_bp.route('/regenerate-codes', methods=['POST'])
@login_required
@admin_required
def regenerate_codes():
    """Regenerate backup codes."""
    password = request.form.get('password')
    
    if not password:
        flash('Password is required to regenerate backup codes.', 'danger')
        return redirect(url_for('two_factor.manage'))
    
    result = regenerate_backup_codes(current_user, password)
    
    if isinstance(result, list):
        flash('Backup codes regenerated successfully. Save them in a secure location!', 'success')
        return render_template('two_factor/backup_codes.html', backup_codes=result)
    else:
        success, message = result
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    
    return redirect(url_for('two_factor.manage'))


@two_factor_bp.route('/backup-codes')
@login_required
@admin_required
def backup_codes():
    """Show backup codes."""
    if not current_user.two_factor_enabled:
        flash('2FA is not enabled for your account.', 'info')
        return redirect(url_for('two_factor.setup'))
    
    backup_codes = current_user.two_factor_backup_codes or []
    return render_template('two_factor/backup_codes.html', backup_codes=backup_codes)


# 2FA middleware for checking verification
def check_2fa_verification():
    """Check if user has completed 2FA verification."""
    if not current_user.is_authenticated:
        return False
    
    if not current_user.two_factor_enabled:
        return True
    
    # Check session
    if session.get('2fa_verified'):
        # Verify session token is still valid
        session_token = session.get('2fa_session_token')
        if session_token and verify_2fa_session(current_user, session_token):
            return True
        else:
            # Clear invalid session
            session.pop('2fa_verified', None)
            session.pop('2fa_session_token', None)
            return False
    
    return False


def require_2fa_verification():
    """Redirect to 2FA verification if needed."""
    if current_user.is_authenticated and current_user.two_factor_enabled:
        if not check_2fa_verification():
            # Store intended page
            session['2fa_next'] = request.url if request.url else url_for('main.dashboard')
            return redirect(url_for('two_factor.verify'))
    return None
