"""Audit logging service for tracking admin actions."""

from flask import request, current_app
from app.models.audit_log import AuditLog
from app.models import User, Entry
import logging

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for logging administrative actions."""
    
    @staticmethod
    def log_admin_action(admin, action, description, target_type=None, target_id=None, 
                         target_name=None, details=None):
        """Log an administrative action."""
        try:
            # Get request information
            ip_address = AuditLogger._get_client_ip()
            user_agent = request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
            
            # Create audit log entry
            log_entry = AuditLog.log_action(
                admin=admin,
                action=action,
                description=description,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"Audit log created: {action} by {admin.username}")
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            return None
    
    @staticmethod
    def log_user_action(admin, action, target_user, details=None):
        """Log an action performed on a user."""
        return AuditLogger.log_admin_action(
            admin=admin,
            action=action,
            description=f"{action.replace('_', ' ').title()} user: {target_user.username}",
            target_type='user',
            target_id=target_user.id,
            target_name=target_user.username,
            details=details
        )
    
    @staticmethod
    def log_entry_action(admin, action, target_entry, details=None):
        """Log an action performed on an entry."""
        return AuditLogger.log_admin_action(
            admin=admin,
            action=action,
            description=f"{action.replace('_', ' ').title()} entry: {target_entry.title or 'Untitled'}",
            target_type='entry',
            target_id=target_entry.id,
            target_name=target_entry.title or 'Untitled',
            details=details
        )
    
    @staticmethod
    def log_system_action(admin, action, description, details=None):
        """Log a system-level action."""
        return AuditLogger.log_admin_action(
            admin=admin,
            action=action,
            description=description,
            target_type='system',
            details=details
        )
    
    @staticmethod
    def log_login_attempt(user, success=True, ip_address=None):
        """Log login attempts (for security monitoring)."""
        try:
            if user.is_admin:  # Only log admin login attempts
                action = 'admin_login_success' if success else 'admin_login_failed'
                description = f"Admin login {'successful' if success else 'failed'} for {user.username}"
                
                # Create audit log entry
                log_entry = AuditLog.log_action(
                    admin=user if success else None,  # Only log admin if successful
                    action=action,
                    description=description,
                    target_type='auth',
                    ip_address=ip_address or AuditLogger._get_client_ip(),
                    user_agent=request.headers.get('User-Agent', 'Unknown') if request else 'Unknown'
                )
                
                logger.info(f"Admin login attempt logged: {action} for {user.username}")
                return log_entry
                
        except Exception as e:
            logger.error(f"Failed to log login attempt: {str(e)}")
            return None
    
    @staticmethod
    def log_password_reset(admin, target_user, temp_password=None):
        """Log password reset actions."""
        details = {
            'reset_method': 'admin_initiated',
            'temp_password_length': len(temp_password) if temp_password else 0
        }
        
        return AuditLogger.log_user_action(
            admin=admin,
            action='password_reset',
            target_user=target_user,
            details=details
        )
    
    @staticmethod
    def log_account_lock(admin, target_user, lock_duration=None):
        """Log account lock actions."""
        details = {
            'lock_duration_days': lock_duration or 30,
            'previous_lock_status': bool(target_user.account_locked_until)
        }
        
        return AuditLogger.log_user_action(
            admin=admin,
            action='user_locked',
            target_user=target_user,
            details=details
        )
    
    @staticmethod
    def log_account_unlock(admin, target_user):
        """Log account unlock actions."""
        details = {
            'previous_lock_status': bool(target_user.account_locked_until),
            'failed_attempts_reset': target_user.failed_login_attempts
        }
        
        return AuditLogger.log_user_action(
            admin=admin,
            action='user_unlocked',
            target_user=target_user,
            details=details
        )
    
    @staticmethod
    def log_user_deletion(admin, target_user):
        """Log user deletion actions."""
        # Get user stats before deletion
        entry_count = target_user.entries.count()
        
        details = {
            'entries_deleted': entry_count,
            'user_email': target_user.email,
            'account_created': target_user.created_at.isoformat() if target_user.created_at else None
        }
        
        return AuditLogger.log_user_action(
            admin=admin,
            action='user_deleted',
            target_user=target_user,
            details=details
        )
    
    @staticmethod
    def log_entry_deletion(admin, target_entry):
        """Log entry deletion actions."""
        details = {
            'entry_content_length': len(target_entry.content) if target_entry.content else 0,
            'entry_created': target_entry.created_at.isoformat() if target_entry.created_at else None,
            'entry_mood': target_entry.mood,
            'entry_tags': target_entry.tags
        }
        
        return AuditLogger.log_entry_action(
            admin=admin,
            action='entry_deleted',
            target_entry=target_entry,
            details=details
        )
    
    @staticmethod
    def log_2fa_action(admin, action, details=None):
        """Log 2FA-related actions."""
        description = f"2FA {action.replace('_', ' ')}"
        
        return AuditLogger.log_system_action(
            admin=admin,
            action=f'2fa_{action}',
            description=description,
            details=details
        )
    
    @staticmethod
    def log_system_settings_change(admin, setting, old_value, new_value):
        """Log system settings changes."""
        description = f"System setting changed: {setting}"
        
        details = {
            'setting': setting,
            'old_value': old_value,
            'new_value': new_value
        }
        
        return AuditLogger.log_system_action(
            admin=admin,
            action='settings_changed',
            description=description,
            details=details
        )
    
    @staticmethod
    def log_security_event(admin, event_type, description, details=None):
        """Log security-related events."""
        return AuditLogger.log_system_action(
            admin=admin,
            action=f'security_{event_type}',
            description=description,
            details=details
        )
    
    @staticmethod
    def _get_client_ip():
        """Get the client IP address from the request."""
        if not request:
            return None
            
        # Check for forwarded headers
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        
        # Fall back to remote address
        return request.remote_addr
    
    @staticmethod
    def get_audit_trail(target_type=None, target_id=None, days=30):
        """Get audit trail for a specific target."""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = AuditLog.query.filter(
            AuditLog.created_at >= start_date
        ).order_by(AuditLog.created_at.desc())
        
        if target_type:
            query = query.filter(AuditLog.target_type == target_type)
        
        if target_id:
            query = query.filter(AuditLog.target_id == target_id)
        
        return query.all()


# Decorator for automatic audit logging
def audit_action(action, target_type=None, description_template=None):
    """Decorator to automatically log admin actions."""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            # Execute the function
            result = f(*args, **kwargs)
            
            # Try to log the action
            try:
                from flask_login import current_user
                
                if current_user.is_authenticated and current_user.is_admin:
                    # Generate description from template if provided
                    description = None
                    if description_template:
                        try:
                            description = description_template.format(*args, **kwargs)
                        except (KeyError, IndexError):
                            description = f"Action: {action}"
                    
                    # Extract target information from kwargs if possible
                    target_id = kwargs.get('user_id') or kwargs.get('entry_id')
                    target_name = kwargs.get('username') or kwargs.get('title')
                    
                    AuditLogger.log_admin_action(
                        admin=current_user,
                        action=action,
                        description=description or f"Action: {action}",
                        target_type=target_type,
                        target_id=target_id,
                        target_name=target_name
                    )
                    
            except Exception as e:
                logger.error(f"Failed to log decorated action: {str(e)}")
            
            return result
        return decorated_function
    return decorator
