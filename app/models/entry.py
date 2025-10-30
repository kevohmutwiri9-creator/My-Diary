from datetime import datetime
from app import db
from sqlalchemy import desc, text, func
from sqlalchemy.orm import validates
from app.models.tag import entry_tags

class Entry(db.Model):
    __tablename__ = 'entries'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    is_private = db.Column(db.Boolean, default=True, index=True)
    mood = db.Column(db.String(50), index=True)
    word_count = db.Column(db.Integer, default=0)
    
    # Foreign key to users table
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    tags = db.relationship(
        'Tag',
        secondary=entry_tags,
        back_populates='entries',
        lazy='joined'
    )
    
    # Indexes for common query patterns
    __table_args__ = (
        db.Index('idx_entry_user_created', 'user_id', 'created_at'),
        db.Index('idx_entry_user_private', 'user_id', 'is_private'),
        db.Index('idx_entry_user_mood', 'user_id', 'mood'),
        db.Index('idx_entry_created', 'created_at')
    )
    
    def __init__(self, **kwargs):
        super(Entry, self).__init__(**kwargs)
        self.update_word_count()
    
    def __repr__(self):
        return f'<Entry {self.id}: {self.title[:30]}>'
    
    @validates('content')
    def update_content(self, key, content):
        """Update content and word count when content changes."""
        self.word_count = len(content.split())
        return content
    
    def update_word_count(self):
        """Update the word count for the entry."""
        if self.content:
            self.word_count = len(self.content.split())
    
    @classmethod
    def get_user_entries(cls, user_id, page=1, per_page=10, search=None, mood=None):
        """Get paginated entries for a user with optional search and mood filter."""
        query = cls.query.filter_by(user_id=user_id)
        
        if search:
            search = f"%{search}%"
            query = query.filter(
                (cls.title.ilike(search)) |
                (cls.content.ilike(search))
            )
        
        if mood:
            query = query.filter_by(mood=mood)
        
        return query.order_by(desc(cls.updated_at)).paginate(
            page=page, per_page=per_page, error_out=False)
    
    @classmethod
    def get_recent_entries(cls, user_id, limit=5):
        """Get most recent entries for a user."""
        return cls.query.filter_by(user_id=user_id)\
            .order_by(desc(cls.updated_at))\
            .limit(limit).all()
    
    @classmethod
    def get_mood_stats(cls, user_id):
        """Get mood statistics for a user."""
        return db.session.query(
            cls.mood,
            func.count(cls.id).label('count')
        ).filter(
            cls.user_id == user_id,
            cls.mood.isnot(None)
        ).group_by(cls.mood).all()
    
    def to_dict(self):
        """Convert entry to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_private': self.is_private,
            'mood': self.mood,
            'word_count': self.word_count,
            'user_id': self.user_id,
            'tags': [tag.name for tag in self.tags]
        }
