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
    last_entry_at = db.Column(db.DateTime, nullable=True)
    streak_count = db.Column(db.Integer, default=0)
    allow_ads = db.Column(db.Boolean, default=False)
    onboarding_state = db.Column(db.JSON, default=dict)
    reminder_opt_in = db.Column(db.Boolean, default=False)
    reminder_frequency = db.Column(db.String(20), default='weekly')
    reminder_last_sent = db.Column(db.DateTime, nullable=True)
    theme_preference = db.Column(db.String(20), default='system')  # system, light, dark, high-contrast, ocean-blue, forest-green
    daily_goal = db.Column(db.Integer, default=1)
    weekly_goal = db.Column(db.Integer, default=7)
    # Social features
    auto_share_anonymous = db.Column(db.Boolean, default=False)
    allow_public_search = db.Column(db.Boolean, default=False)
    show_in_community = db.Column(db.Boolean, default=True)
    default_privacy = db.Column(db.Boolean, default=True)
    # Security features
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32), nullable=True)
    two_factor_backup_codes = db.Column(db.JSON, nullable=True)
    encryption_enabled = db.Column(db.Boolean, default=False)
    encryption_key = db.Column(db.String(64), nullable=True)
    # Internationalization
    language_preference = db.Column(db.String(5), default='en')  # en, es, fr, de, etc.
    timezone = db.Column(db.String(50), default='UTC')
    date_format = db.Column(db.String(10), default='medium')  # short, medium, long, full
    time_format = db.Column(db.String(5), default='24h')  # 12h, 24h
    currency = db.Column(db.String(3), default='USD')  # USD, EUR, GBP, etc.
    number_format = db.Column(db.String(10), default='decimal')  # decimal, comma, space
    
    # Subscription/Premium features
    subscription_tier = db.Column(db.String(20), default='free')  # free, premium, pro
    subscription_status = db.Column(db.String(20), default='inactive')  # active, cancelled, expired, inactive
    subscription_started_at = db.Column(db.DateTime, nullable=True)
    subscription_ends_at = db.Column(db.DateTime, nullable=True)
    paypal_subscription_id = db.Column(db.String(100), nullable=True)
    last_payment_at = db.Column(db.DateTime, nullable=True)
    next_billing_date = db.Column(db.DateTime, nullable=True)
    auto_renew = db.Column(db.Boolean, default=True)
    trial_used = db.Column(db.Boolean, default=False)
    trial_started_at = db.Column(db.DateTime, nullable=True)
    trial_ends_at = db.Column(db.DateTime, nullable=True)
    
    # Profile
    profile_picture = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    # Relationships
    entries = db.relationship('Entry', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    
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

    def update_streak(self, entry_time=None):
        from datetime import datetime, timedelta
        entry_time = entry_time or datetime.utcnow()
        if self.last_entry_at:
            days_since_last = (entry_time.date() - self.last_entry_at.date()).days
            if days_since_last == 0:
                pass
            elif days_since_last == 1:
                self.streak_count = (self.streak_count or 0) + 1
            else:
                self.streak_count = 1
        else:
            self.streak_count = 1
        self.last_entry_at = entry_time
    
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

    # Onboarding helpers
    def get_onboarding_state(self):
        return self.onboarding_state or {}

    def has_completed_task(self, task_key):
        state = self.get_onboarding_state()
        return bool(state.get(task_key))

    def mark_onboarding_task(self, task_key):
        if self.has_completed_task(task_key):
            return False
        state = self.get_onboarding_state().copy()
        state[task_key] = datetime.utcnow().isoformat()
        self.onboarding_state = state
        return True

    def get_profile_picture_url(self):
        """Get the URL for the user's profile picture."""
        if self.profile_picture:
            return f"/static/uploads/profile_pictures/{self.profile_picture}"
        # Generate avatar based on username
        return f"https://ui-avatars.com/api/?name={self.username}&background=random&color=fff&size=128"

    def update_profile_picture(self, filename):
        """Update the user's profile picture."""
        self.profile_picture = filename

    # Subscription methods
    def is_premium(self):
        """Check if user has premium subscription."""
        return self.subscription_tier in ['premium', 'pro'] and self.subscription_status == 'active'
    
    def is_pro(self):
        """Check if user has pro subscription."""
        return self.subscription_tier == 'pro' and self.subscription_status == 'active'
    
    def is_trial_active(self):
        """Check if user has active trial."""
        if not self.trial_started_at or not self.trial_ends_at:
            return False
        return datetime.utcnow() < self.trial_ends_at
    
    def can_start_trial(self):
        """Check if user can start a trial."""
        return not self.trial_used and not self.is_premium()
    
    def start_trial(self, tier='premium', days=14):
        """Start a free trial."""
        if not self.can_start_trial():
            return False
        
        self.trial_used = True
        self.trial_started_at = datetime.utcnow()
        self.trial_ends_at = datetime.utcnow() + timedelta(days=days)
        self.subscription_tier = tier
        self.subscription_status = 'active'
        
        db.session.commit()
        return True
    
    def upgrade_subscription(self, tier, paypal_subscription_id=None):
        """Upgrade user subscription."""
        self.subscription_tier = tier
        self.subscription_status = 'active'
        self.subscription_started_at = datetime.utcnow()
        self.paypal_subscription_id = paypal_subscription_id
        self.last_payment_at = datetime.utcnow()
        
        # Set next billing date based on tier
        if tier == 'premium':
            self.subscription_ends_at = datetime.utcnow() + timedelta(days=30)
        elif tier == 'pro':
            self.subscription_ends_at = datetime.utcnow() + timedelta(days=30)
        
        self.next_billing_date = self.subscription_ends_at
        
        db.session.commit()
        return True
    
    def cancel_subscription(self):
        """Cancel subscription."""
        self.subscription_status = 'cancelled'
        self.auto_renew = False
        db.session.commit()
        return True
    
    def extend_subscription(self, days=30):
        """Extend subscription period."""
        if self.subscription_ends_at:
            self.subscription_ends_at += timedelta(days=days)
        else:
            self.subscription_ends_at = datetime.utcnow() + timedelta(days=days)
        
        self.next_billing_date = self.subscription_ends_at
        db.session.commit()
        return True
    
    def get_subscription_features(self):
        """Get available features based on subscription tier."""
        features = {
            'free': {
                'max_entries': 100,
                'max_photos': 10,
                'ai_insights': False,
                'advanced_analytics': False,
                'templates': 5,
                'export_formats': ['txt'],
                'priority_support': False,
                'ads': True,
                'voice_entries': False,
                'collaboration': False
            },
            'premium': {
                'max_entries': float('inf'),
                'max_photos': 100,
                'ai_insights': True,
                'advanced_analytics': True,
                'templates': 50,
                'export_formats': ['txt', 'pdf', 'json'],
                'priority_support': True,
                'ads': False,
                'voice_entries': True,
                'collaboration': False
            },
            'pro': {
                'max_entries': float('inf'),
                'max_photos': float('inf'),
                'ai_insights': True,
                'advanced_analytics': True,
                'templates': float('inf'),
                'export_formats': ['txt', 'pdf', 'json', 'csv', 'docx'],
                'priority_support': True,
                'ads': False,
                'voice_entries': True,
                'collaboration': True
            }
        }
        
        return features.get(self.subscription_tier, features['free'])
    
    def check_subscription_limits(self):
        """Check if user is approaching subscription limits."""
        if self.is_premium():
            return {'status': 'ok', 'message': 'No limits for premium users'}
        
        features = self.get_subscription_features()
        current_entries = self.entries.count()
        
        warnings = []
        
        if current_entries >= features['max_entries'] * 0.8:
            warnings.append(f'You have used {current_entries} of {features["max_entries"]} entries')
        
        return {
            'status': 'warning' if warnings else 'ok',
            'warnings': warnings,
            'features': features
        }

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))