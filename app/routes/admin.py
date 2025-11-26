"""Admin routes for user and system management."""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from app import db
from app.models import User, Entry
from app.models.audit_log import AuditLog
from app.utils.decorators import admin_required
from app.services.email_service import send_password_reset_email, send_admin_action_email
from app.services.audit_service import AuditLogger

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system statistics."""
    # Get system statistics
    total_users = User.query.count()
    total_entries = Entry.query.count()
    active_users = User.query.filter(
        User.last_seen >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    # Recent entries
    recent_entries = Entry.query.order_by(desc(Entry.created_at)).limit(10).all()
    
    # Recent users
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    
    # Storage usage estimation
    avg_entry_size = 500  # Rough estimate in bytes
    storage_usage = total_entries * avg_entry_size
    
    stats = {
        'total_users': total_users,
        'total_entries': total_entries,
        'active_users': active_users,
        'storage_usage_mb': round(storage_usage / (1024 * 1024), 2),
        'recent_entries': recent_entries,
        'recent_users': recent_users
    }
    
    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management page."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    users = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users, search=search)


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Reset a user's password."""
    user = User.query.get_or_404(user_id)
    
    # Generate a temporary password
    import secrets
    import string
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(12))
    
    user.set_password(temp_password)
    user.failed_login_attempts = 0
    user.account_locked_until = None
    db.session.commit()
    
    # Log the action
    AuditLogger.log_password_reset(current_user, user, temp_password)
    
    # Send email notification
    email_sent = send_password_reset_email(user, temp_password)
    
    if email_sent:
        flash(f'Password reset for {user.username}. New password sent to their email.', 'success')
    else:
        flash(f'Password reset for {user.username}. New password: {temp_password} (Email failed to send)', 'warning')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/lock', methods=['POST'])
@login_required
@admin_required
def lock_user(user_id):
    """Lock a user account."""
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash('Cannot lock admin user.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.account_locked_until = datetime.utcnow() + timedelta(days=30)
    db.session.commit()
    
    # Log the action
    AuditLogger.log_account_lock(current_user, user, lock_duration=30)
    
    # Send email notification
    send_admin_action_email(user, 'locked', 'Your account has been locked for 30 days due to security concerns.')
    
    flash(f'Account {user.username} has been locked for 30 days.', 'warning')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@login_required
@admin_required
def unlock_user(user_id):
    """Unlock a user account."""
    user = User.query.get_or_404(user_id)
    
    user.account_locked_until = None
    user.failed_login_attempts = 0
    db.session.commit()
    
    # Log the action
    AuditLogger.log_account_unlock(current_user, user)
    
    # Send email notification
    send_admin_action_email(user, 'unlocked', 'Your account has been unlocked and you can now log in normally.')
    
    flash(f'Account {user.username} has been unlocked.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user and all their entries."""
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash('Cannot delete admin user.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Log the action before deletion
    AuditLogger.log_user_deletion(current_user, user)
    
    # Send email notification before deletion
    send_admin_action_email(user, 'deleted', 'Your account and all associated data have been permanently deleted from our system.')
    
    # Store user info for flash message
    username = user.username
    email = user.email
    
    # Delete all user entries first
    Entry.query.filter_by(user_id=user_id).delete()
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} and all their entries have been deleted. Notification sent to {email}', 'warning')
    return redirect(url_for('admin.users'))


@admin_bp.route('/entries')
@login_required
@admin_required
def entries():
    """Content moderation - view all entries."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Entry.query.join(User)
    
    if search:
        query = query.filter(
            (Entry.title.ilike(f'%{search}%')) |
            (Entry.content.ilike(f'%{search}%')) |
            (User.username.ilike(f'%{search}%'))
        )
    
    entries = query.order_by(desc(Entry.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/entries.html', entries=entries, search=search)


@admin_bp.route('/entries/<int:entry_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_entry(entry_id):
    """Delete an entry."""
    entry = Entry.query.get_or_404(entry_id)
    
    # Log the action before deletion
    AuditLogger.log_entry_deletion(current_user, entry)
    
    db.session.delete(entry)
    db.session.commit()
    
    flash(f'Entry "{entry.title}" has been deleted.', 'warning')
    return redirect(url_for('admin.entries'))


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """System settings page."""
    # Get system configuration
    config = current_app.config
    
    # Calculate some system metrics
    total_entries = Entry.query.count()
    total_users = User.query.count()
    
    system_info = {
        'app_version': config.get('VERSION', '1.0.0'),
        'debug_mode': config.get('DEBUG', False),
        'database_uri': config.get('SQLALCHEMY_DATABASE_URI', '').split('@')[-1] if '@' in config.get('SQLALCHEMY_DATABASE_URI', '') else 'N/A',
        'secret_key_set': bool(config.get('SECRET_KEY')),
        'total_entries': total_entries,
        'total_users': total_users,
        'maintenance_mode': config.get('MAINTENANCE_MODE', False)
    }
    
    return render_template('admin/settings.html', system_info=system_info)


@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """API endpoint for real-time statistics."""
    total_users = User.query.count()
    total_entries = Entry.query.count()
    active_today = User.query.filter(
        User.last_seen >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    
    return jsonify({
        'total_users': total_users,
        'total_entries': total_entries,
        'active_today': active_today,
        'timestamp': datetime.utcnow().isoformat()
    })


@admin_bp.route('/audit-log')
@login_required
@admin_required
def audit_log():
    """View audit log of admin actions."""
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    target_filter = request.args.get('target_type', '')
    
    # Build query
    query = AuditLog.query.order_by(AuditLog.created_at.desc())
    
    # Apply filters
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    
    if target_filter:
        query = query.filter(AuditLog.target_type == target_filter)
    
    # Paginate
    logs = query.paginate(page=page, per_page=50, error_out=False)
    
    # Get filter options
    actions = db.session.query(AuditLog.action).distinct().all()
    target_types = db.session.query(AuditLog.target_type).filter(AuditLog.target_type.isnot(None)).distinct().all()
    
    return render_template('admin/audit_log.html', 
                         logs=logs, 
                         actions=[a[0] for a in actions],
                         target_types=[t[0] for t in target_types],
                         current_action=action_filter,
                         current_target=target_filter)
