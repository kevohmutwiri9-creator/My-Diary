"""Email service for sending notifications."""

from flask import current_app, render_template
from flask_mail import Message
from app import mail
import logging

logger = logging.getLogger(__name__)


def send_password_reset_email(user, new_password):
    """Send password reset notification to user."""
    try:
        subject = "Password Reset - My Diary"
        
        # Create email message
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=render_template(
                'email/password_reset.html',
                user=user,
                new_password=new_password
            ),
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mydiary.com')
        )
        
        # Send email
        mail.send(msg)
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False


def send_welcome_email(user):
    """Send welcome email to new user."""
    try:
        subject = "Welcome to My Diary!"
        
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=render_template(
                'email/welcome.html',
                user=user
            ),
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mydiary.com')
        )
        
        mail.send(msg)
        logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        return False


def send_account_locked_email(user):
    """Send notification when account is locked."""
    try:
        subject = "Account Locked - My Diary"
        
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=render_template(
                'email/account_locked.html',
                user=user
            ),
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mydiary.com')
        )
        
        mail.send(msg)
        logger.info(f"Account locked email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send account locked email to {user.email}: {str(e)}")
        return False


def send_admin_action_email(user, action, details=None):
    """Send notification about admin actions on user account."""
    try:
        subject = f"Account {action.title()} - My Diary"
        
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=render_template(
                'email/admin_action.html',
                user=user,
                action=action,
                details=details
            ),
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mydiary.com')
        )
        
        mail.send(msg)
        logger.info(f"Admin action email sent to {user.email} for action: {action}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send admin action email to {user.email}: {str(e)}")
        return False
