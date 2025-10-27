import re
import hmac
import hashlib
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask_login import UserMixin
from app import db, login_manager
from wtforms import ValidationError

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))  # Increased length for hashed passwords
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    last_password_change = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    entries = db.relationship('Entry', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        password = kwargs.pop('password', None)
        email = kwargs.get('email')
        if email:
            kwargs['email'] = email.lower()

        super(User, self).__init__(**kwargs)

        if password:
            self.set_password(password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password against security requirements."""
        config = current_app.config
        
        if len(password) < config.get('PASSWORD_MIN_LENGTH', 12):
            raise ValidationError(f'Password must be at least {config["PASSWORD_MIN_LENGTH"]} characters long')
        
        if config.get('PASSWORD_REQUIRE_UPPERCASE', True) and not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
            
        if config.get('PASSWORD_REQUIRE_LOWERCASE', True) and not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
            
        if config.get('PASSWORD_REQUIRE_NUMBER', True) and not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one number')
            
        if config.get('PASSWORD_REQUIRE_SPECIAL', True) and not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError('Password must contain at least one special character')
    
    def set_password(self, password):
        """Set password after validating it meets requirements."""
        self.validate_password_strength(password)
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:600000')
        self.last_password_change = datetime.utcnow()
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        if self.account_locked_until and self.account_locked_until > datetime.utcnow():
            return False

        is_correct = False
        legacy_hash = False

        try:
            is_correct = check_password_hash(self.password_hash, password)
        except ValueError:
            is_correct = self._check_legacy_password_hash(password)
            legacy_hash = is_correct

        if is_correct:
            self.failed_login_attempts = 0
            self.account_locked_until = None

            # Seamlessly upgrade legacy hashes to the stronger default
            if legacy_hash:
                self.set_password(password)
                db.session.commit()
        else:
            self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
            if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
                self.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
            db.session.commit()

        return is_correct

    def _check_legacy_password_hash(self, password):
        """Support legacy Werkzeug 'sha256' hashes for existing users."""
        stored_hash = self.password_hash or ''

        if not stored_hash.startswith('sha256$'):
            return False

        try:
            _, salt, hash_value = stored_hash.split('$', 2)
        except ValueError:
            return False

        candidate = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return hmac.compare_digest(candidate, hash_value)
    
    def is_account_locked(self):
        """Check if the account is currently locked."""
        return self.account_locked_until and self.account_locked_until > datetime.utcnow()

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))