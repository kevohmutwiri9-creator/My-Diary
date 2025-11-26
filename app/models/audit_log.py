"""Audit log model for tracking admin actions."""

from datetime import datetime
from app import db


class AuditLog(db.Model):
    """Model for logging administrative actions."""
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Admin who performed the action
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admin = db.relationship('User', foreign_keys=[admin_id], backref='admin_actions')
    
    # Action details
    action = db.Column(db.String(100), nullable=False)  # e.g., 'user_locked', 'password_reset'
    target_type = db.Column(db.String(50), nullable=True)  # e.g., 'user', 'entry', 'system'
    target_id = db.Column(db.Integer, nullable=True)
    target_name = db.Column(db.String(255), nullable=True)  # Human-readable target identifier
    
    # Action details
    description = db.Column(db.Text, nullable=False)
    details = db.Column(db.JSON, nullable=True)  # Additional structured data
    
    # Request information
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.admin.username}>'
    
    @classmethod
    def log_action(cls, admin, action, description, target_type=None, target_id=None, 
                   target_name=None, details=None, ip_address=None, user_agent=None):
        """Create a new audit log entry."""
        log_entry = cls(
            admin_id=admin.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            description=description,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        return log_entry
    
    @classmethod
    def get_recent_logs(cls, limit=100, admin_id=None, action=None, target_type=None):
        """Get recent audit logs with optional filtering."""
        query = cls.query.order_by(cls.created_at.desc())
        
        if admin_id:
            query = query.filter(cls.admin_id == admin_id)
        
        if action:
            query = query.filter(cls.action == action)
        
        if target_type:
            query = query.filter(cls.target_type == target_type)
        
        return query.limit(limit).all()
    
    @classmethod
    def get_logs_by_date_range(cls, start_date, end_date, admin_id=None, action=None):
        """Get audit logs within a date range."""
        query = cls.query.filter(
            cls.created_at >= start_date,
            cls.created_at <= end_date
        ).order_by(cls.created_at.desc())
        
        if admin_id:
            query = query.filter(cls.admin_id == admin_id)
        
        if action:
            query = query.filter(cls.action == action)
        
        return query.all()
    
    @classmethod
    def get_action_statistics(cls, days=30):
        """Get statistics of actions performed in the last N days."""
        from datetime import timedelta
        from sqlalchemy import func
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Action counts
        action_counts = db.session.query(
            cls.action,
            func.count(cls.id).label('count')
        ).filter(
            cls.created_at >= start_date
        ).group_by(cls.action).all()
        
        # Admin activity
        admin_activity = db.session.query(
            cls.admin_id,
            func.count(cls.id).label('count')
        ).filter(
            cls.created_at >= start_date
        ).group_by(cls.admin_id).all()
        
        # Target type distribution
        target_counts = db.session.query(
            cls.target_type,
            func.count(cls.id).label('count')
        ).filter(
            cls.created_at >= start_date,
            cls.target_type.isnot(None)
        ).group_by(cls.target_type).all()
        
        return {
            'action_counts': dict(action_counts),
            'admin_activity': dict(admin_activity),
            'target_counts': dict(target_counts),
            'total_actions': sum(count for _, count in action_counts)
        }
    
    def to_dict(self):
        """Convert audit log to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'admin': self.admin.username if self.admin else 'Unknown',
            'admin_id': self.admin_id,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'target_name': self.target_name,
            'description': self.description,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
