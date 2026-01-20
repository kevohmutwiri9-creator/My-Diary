from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
import secrets

from . import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    theme = db.Column(db.String(20), default="dark", nullable=False)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Email notification preferences
    email_daily_reminders = db.Column(db.Boolean, default=True, nullable=False)
    email_weekly_summary = db.Column(db.Boolean, default=True, nullable=False)
    email_monthly_insights = db.Column(db.Boolean, default=True, nullable=False)
    last_daily_reminder = db.Column(db.DateTime, nullable=True)
    last_weekly_summary = db.Column(db.DateTime, nullable=True)
    last_monthly_insights = db.Column(db.DateTime, nullable=True)

    entries = db.relationship("Entry", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self) -> str:
        """Generate a secure password reset token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        return self.reset_token
    
    def verify_reset_token(self, token: str) -> bool:
        """Verify password reset token"""
        if (self.reset_token != token or 
            not self.reset_token_expires or 
            self.reset_token_expires < datetime.utcnow()):
            return False
        return True
    
    def clear_reset_token(self) -> None:
        """Clear password reset token"""
        self.reset_token = None
        self.reset_token_expires = None
        db.session.commit()


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    mood = db.Column(db.String(30), nullable=True)
    tags = db.Column(db.String(300), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    
    # AI Analysis fields
    sentiment = db.Column(db.String(20), nullable=True)  # positive, negative, neutral
    emotions = db.Column(db.Text, nullable=True)  # JSON string of detected emotions
    ai_insights = db.Column(db.Text, nullable=True)  # AI-generated insights
    mood_score = db.Column(db.Float, nullable=True)  # -1.0 to 1.0 sentiment score

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    user = db.relationship("User", back_populates="entries")

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
