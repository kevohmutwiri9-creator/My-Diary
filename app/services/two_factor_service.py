"""Two-Factor Authentication service for enhanced security."""

import pyotp
import qrcode
import io
import base64
from flask import current_app
from app import db
from app.models import User
import logging

logger = logging.getLogger(__name__)


def generate_2fa_secret():
    """Generate a new 2FA secret for a user."""
    return pyotp.random_base32()


def generate_qr_code(user, secret):
    """Generate QR code for 2FA setup."""
    # Create TOTP URI
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name="My Diary Admin"
    )
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for HTML display
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def verify_2fa_token(user, token):
    """Verify a 2FA token for a user."""
    if not user.two_factor_enabled or not user.two_factor_secret:
        return False
    
    totp = pyotp.TOTP(user.two_factor_secret)
    return totp.verify(token, valid_window=1)  # Allow 1 step tolerance


def enable_2fa_for_user(user):
    """Enable 2FA for a user and return setup details."""
    if not user.is_admin:
        raise ValueError("2FA is only available for admin users")
    
    # Generate secret
    secret = generate_2fa_secret()
    
    # Generate backup codes
    backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]
    
    # Store in user model (but don't enable yet until verification)
    user.two_factor_secret = secret
    user.two_factor_backup_codes = backup_codes
    
    # Generate QR code
    qr_code = generate_qr_code(user, secret)
    
    return {
        'secret': secret,
        'qr_code': qr_code,
        'backup_codes': backup_codes
    }


def confirm_2fa_setup(user, verification_token):
    """Confirm and enable 2FA after user verification."""
    if not user.two_factor_secret:
        return False, "No 2FA setup in progress"
    
    # Verify the token
    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(verification_token, valid_window=1):
        return False, "Invalid verification code"
    
    # Enable 2FA
    user.two_factor_enabled = True
    db.session.commit()
    
    logger.info(f"2FA enabled for admin user: {user.username}")
    return True, "2FA enabled successfully"


def disable_2fa_for_user(user, password):
    """Disable 2FA for a user (requires password confirmation)."""
    if not user.check_password(password):
        return False, "Invalid password"
    
    user.two_factor_enabled = False
    user.two_factor_secret = None
    user.two_factor_backup_codes = None
    db.session.commit()
    
    logger.info(f"2FA disabled for admin user: {user.username}")
    return True, "2FA disabled successfully"


def verify_backup_code(user, backup_code):
    """Verify and consume a backup code."""
    if not user.two_factor_backup_codes:
        return False
    
    if backup_code in user.two_factor_backup_codes:
        # Remove the used backup code
        user.two_factor_backup_codes.remove(backup_code)
        db.session.commit()
        
        logger.warning(f"Backup code used for admin user: {user.username}")
        return True
    
    return False


def regenerate_backup_codes(user, password):
    """Regenerate backup codes for a user."""
    if not user.check_password(password):
        return False, "Invalid password"
    
    if not user.two_factor_enabled:
        return False, "2FA is not enabled"
    
    # Generate new backup codes
    backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]
    user.two_factor_backup_codes = backup_codes
    db.session.commit()
    
    logger.info(f"Backup codes regenerated for admin user: {user.username}")
    return backup_codes


def is_2fa_required_for_user(user):
    """Check if 2FA is required for a user."""
    return user.is_admin and user.two_factor_enabled


def create_2fa_session(user):
    """Create a temporary session after 2FA verification."""
    import secrets
    from datetime import datetime, timedelta
    
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    
    # Store in user session data
    session_data = user.get_onboarding_state().copy()
    session_data['2fa_session_token'] = token
    session_data['2fa_session_expires'] = expires.isoformat()
    user.onboarding_state = session_data
    db.session.commit()
    
    return token


def verify_2fa_session(user, token):
    """Verify a 2FA session token."""
    session_data = user.get_onboarding_state()
    
    stored_token = session_data.get('2fa_session_token')
    expires_str = session_data.get('2fa_session_expires')
    
    if not stored_token or not expires_str:
        return False
    
    if stored_token != token:
        return False
    
    try:
        expires = datetime.fromisoformat(expires_str)
        if datetime.utcnow() > expires:
            return False
    except ValueError:
        return False
    
    return True


def clear_2fa_session(user):
    """Clear a 2FA session token."""
    session_data = user.get_onboarding_state().copy()
    session_data.pop('2fa_session_token', None)
    session_data.pop('2fa_session_expires', None)
    user.onboarding_state = session_data
    db.session.commit()
