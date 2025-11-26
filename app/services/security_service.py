import secrets
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app import db
from app.models.user import User
from app.models.entry import Entry

# Generate encryption key
def generate_encryption_key(user_password: str, salt: bytes = None) -> bytes:
    """Generate encryption key from user password."""
    if salt is None:
        salt = b'salt_for_diary_app'  # In production, use unique salt per user
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(user_password.encode()))
    return key

def encrypt_entry_content(content: str, encryption_key: bytes) -> str:
    """Encrypt entry content."""
    f = Fernet(encryption_key)
    encrypted_content = f.encrypt(content.encode())
    return base64.urlsafe_b64encode(encrypted_content).decode()

def decrypt_entry_content(encrypted_content: str, encryption_key: bytes) -> str:
    """Decrypt entry content."""
    f = Fernet(encryption_key)
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_content.encode())
    decrypted_content = f.decrypt(encrypted_bytes)
    return decrypted_content.decode()

def setup_2fa(user_id: int) -> Dict[str, Any]:
    """Setup 2FA for user."""
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}
    
    # Generate secret key
    secret = pyotp.random_base32()
    user.two_factor_secret = secret
    user.two_factor_enabled = False  # Not enabled until verified
    
    # Generate QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name="My Diary"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        'success': True,
        'secret': secret,
        'qr_code': qr_code_data,
        'manual_entry_key': secret
    }

def verify_2fa_setup(user_id: int, token: str) -> Dict[str, Any]:
    """Verify 2FA setup with token."""
    user = User.query.get(user_id)
    if not user or not user.two_factor_secret:
        return {'success': False, 'error': '2FA not setup'}
    
    totp = pyotp.TOTP(user.two_factor_secret)
    if totp.verify(token, valid_window=1):
        user.two_factor_enabled = True
        db.session.commit()
        return {'success': True, 'message': '2FA enabled successfully'}
    else:
        return {'success': False, 'error': 'Invalid token'}

def verify_2fa_token(user_id: int, token: str) -> bool:
    """Verify 2FA token for login."""
    user = User.query.get(user_id)
    if not user or not user.two_factor_enabled or not user.two_factor_secret:
        return False
    
    totp = pyotp.TOTP(user.two_factor_secret)
    return totp.verify(token, valid_window=1)

def disable_2fa(user_id: int, password: str) -> Dict[str, Any]:
    """Disable 2FA for user."""
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}
    
    # Verify password
    if not user.check_password(password):
        return {'success': False, 'error': 'Invalid password'}
    
    user.two_factor_enabled = False
    user.two_factor_secret = None
    db.session.commit()
    
    return {'success': True, 'message': '2FA disabled successfully'}

def backup_user_data(user_id: int, encryption_key: bytes) -> Dict[str, Any]:
    """Create encrypted backup of user data."""
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}
    
    # Get all entries
    entries = Entry.query.filter_by(user_id=user_id).all()
    
    # Create backup data
    backup_data = {
        'user_info': {
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.isoformat(),
            'export_date': datetime.utcnow().isoformat()
        },
        'entries': []
    }
    
    for entry in entries:
        entry_data = {
            'title': entry.title,
            'content': entry.content,
            'mood': entry.mood,
            'created_at': entry.created_at.isoformat(),
            'is_private': entry.is_private
        }
        backup_data['entries'].append(entry_data)
    
    # Encrypt backup
    import json
    backup_json = json.dumps(backup_data)
    encrypted_backup = encrypt_entry_content(backup_json, encryption_key)
    
    return {
        'success': True,
        'backup_data': encrypted_backup,
        'filename': f"diary_backup_{user.username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.encrypted"
    }

def restore_user_data(backup_data: str, encryption_key: bytes, user_id: int) -> Dict[str, Any]:
    """Restore user data from encrypted backup."""
    try:
        # Decrypt backup
        decrypted_json = decrypt_entry_content(backup_data, encryption_key)
        backup = json.loads(decrypted_json)
        
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Verify backup belongs to user (check email/username)
        if backup['user_info']['email'] != user.email:
            return {'success': False, 'error': 'Backup does not belong to this user'}
        
        # Restore entries (merge with existing)
        restored_count = 0
        for entry_data in backup['entries']:
            # Check if entry already exists (by created_at)
            existing_entry = Entry.query.filter_by(
                user_id=user_id,
                created_at=datetime.fromisoformat(entry_data['created_at'])
            ).first()
            
            if not existing_entry:
                new_entry = Entry(
                    title=entry_data['title'],
                    content=entry_data['content'],
                    mood=entry_data['mood'],
                    is_private=entry_data['is_private'],
                    user_id=user_id,
                    created_at=datetime.fromisoformat(entry_data['created_at'])
                )
                db.session.add(new_entry)
                restored_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Successfully restored {restored_count} entries'
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Restore failed: {str(e)}'}

def get_security_settings(user_id: int) -> Dict[str, Any]:
    """Get user's security settings."""
    user = User.query.get(user_id)
    if not user:
        return {}
    
    return {
        'two_factor_enabled': user.two_factor_enabled or False,
        'two_factor_setup_complete': bool(user.two_factor_secret),
        'login_attempts': user.failed_login_attempts or 0,
        'account_locked': user.is_account_locked(),
        'last_password_change': user.last_password_change.isoformat() if user.last_password_change else None,
        'encryption_enabled': getattr(user, 'encryption_enabled', False)
    }

def update_security_settings(user_id: int, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Update user's security settings."""
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}
    
    try:
        if 'encryption_enabled' in settings:
            user.encryption_enabled = settings['encryption_enabled']
        
        db.session.commit()
        return {'success': True, 'message': 'Security settings updated'}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Update failed: {str(e)}'}

def generate_session_token() -> str:
    """Generate secure session token."""
    return secrets.token_urlsafe(32)

def validate_session_token(token: str, max_age: int = 3600) -> bool:
    """Validate session token (simplified implementation)."""
    # In production, store tokens in database with expiration
    return len(token) >= 32 and token.isalnum()

def get_security_audit_log(user_id: int, limit: int = 50) -> list:
    """Get security audit log for user (simplified)."""
    # In production, this would query a proper audit log table
    user = User.query.get(user_id)
    if not user:
        return []
    
    # Mock audit data
    audit_log = [
        {
            'timestamp': user.last_password_change or user.created_at,
            'action': 'Password changed',
            'ip_address': '127.0.0.1',
            'user_agent': 'Browser'
        }
    ]
    
    if user.failed_login_attempts > 0:
        audit_log.append({
            'timestamp': datetime.utcnow(),
            'action': f'Failed login attempt ({user.failed_login_attempts} total)',
            'ip_address': '127.0.0.1',
            'user_agent': 'Browser'
        })
    
    return audit_log[:limit]
