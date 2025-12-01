"""
Templates and Writing Prompts Models for My Diary App
"""

from datetime import datetime, timedelta
from app import db
import json
from sqlalchemy import text
from sqlalchemy.orm import relationship


class JournalTemplate(db.Model):
    """Journal template model"""
    __tablename__ = 'journal_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    tags = db.Column(db.Text)  # JSON array of tags
    is_public = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship('User', back_populates='created_templates')
    template_ratings = relationship('TemplateRating', back_populates='template', cascade='all, delete-orphan')
    template_usages = relationship('TemplateUsage', back_populates='template', cascade='all, delete-orphan')
    
    def get_tags_list(self):
        """Get tags as list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []
    
    def set_tags_list(self, tags_list):
        """Set tags from list"""
        if tags_list:
            self.tags = json.dumps(tags_list)
        else:
            self.tags = None
    
    def update_rating(self):
        """Update average rating"""
        if self.rating_count > 0:
            total_rating = sum(rating.rating for rating in self.template_ratings)
            self.rating = total_rating / self.rating_count
        else:
            self.rating = 0.0
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        db.session.commit()
    
    def to_dict(self, include_content=True):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'tags': self.get_tags_list(),
            'is_public': self.is_public,
            'is_premium': self.is_premium,
            'usage_count': self.usage_count,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_content:
            data['content'] = self.content
        
        if self.creator:
            data['creator'] = {
                'id': self.creator.id,
                'username': self.creator.username
            }
        
        return data


class WritingPrompt(db.Model):
    """Writing prompt model"""
    __tablename__ = 'writing_prompts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    tags = db.Column(db.Text)  # JSON array of tags
    is_public = db.Column(db.Boolean, default=True)
    is_premium = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    estimated_time = db.Column(db.Integer)  # Estimated writing time in minutes
    word_count_goal = db.Column(db.Integer)  # Suggested word count
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship('User', back_populates='created_prompts')
    prompt_ratings = relationship('PromptRating', back_populates='prompt', cascade='all, delete-orphan')
    prompt_responses = relationship('PromptResponse', back_populates='prompt', cascade='all, delete-orphan')
    
    def get_tags_list(self):
        """Get tags as list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []
    
    def set_tags_list(self, tags_list):
        """Set tags from list"""
        if tags_list:
            self.tags = json.dumps(tags_list)
        else:
            self.tags = None
    
    def update_rating(self):
        """Update average rating"""
        if self.rating_count > 0:
            total_rating = sum(rating.rating for rating in self.prompt_ratings)
            self.rating = total_rating / self.rating_count
        else:
            self.rating = 0.0
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        db.session.commit()
    
    def to_dict(self, include_stats=True):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'prompt_text': self.prompt_text,
            'category': self.category,
            'difficulty': self.difficulty,
            'tags': self.get_tags_list(),
            'is_public': self.is_public,
            'is_premium': self.is_premium,
            'estimated_time': self.estimated_time,
            'word_count_goal': self.word_count_goal,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_stats:
            data['usage_count'] = self.usage_count
            data['rating'] = self.rating
            data['rating_count'] = self.rating_count
        
        if self.creator:
            data['creator'] = {
                'id': self.creator.id,
                'username': self.creator.username
            }
        
        return data


class TemplateRating(db.Model):
    """Template rating model"""
    __tablename__ = 'template_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('journal_templates.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship('JournalTemplate', back_populates='template_ratings')
    user = relationship('User')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('template_id', 'user_id'),)


class PromptRating(db.Model):
    """Writing prompt rating model"""
    __tablename__ = 'prompt_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('writing_prompts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    prompt = relationship('WritingPrompt', back_populates='prompt_ratings')
    user = relationship('User')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('prompt_id', 'user_id'),)


class TemplateUsage(db.Model):
    """Template usage tracking model"""
    __tablename__ = 'template_usages'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('journal_templates.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey('entries.id'), nullable=True)  # If usage resulted in an entry
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship('JournalTemplate', back_populates='template_usages')
    user = relationship('User')
    entry = relationship('Entry')


class PromptResponse(db.Model):
    """Writing prompt response model"""
    __tablename__ = 'prompt_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('writing_prompts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey('entries.id'), nullable=True)  # If response became an entry
    response_text = db.Column(db.Text)
    word_count = db.Column(db.Integer, default=0)
    time_spent = db.Column(db.Integer)  # Time spent in minutes
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    prompt = relationship('WritingPrompt', back_populates='prompt_responses')
    user = relationship('User')
    entry = relationship('Entry')


class DailyPrompt(db.Model):
    """Daily prompt model"""
    __tablename__ = 'daily_prompts'
    
    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('writing_prompts.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    prompt = relationship('WritingPrompt')


class PromptCollection(db.Model):
    """Prompt collection model"""
    __tablename__ = 'prompt_collections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')
    is_public = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship('User')
    collection_items = relationship('CollectionItem', back_populates='collection', cascade='all, delete-orphan')
    
    def to_dict(self, include_prompts=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'is_public': self.is_public,
            'is_premium': self.is_premium,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_prompts:
            data['prompts'] = [item.prompt.to_dict() for item in self.collection_items]
        
        if self.creator:
            data['creator'] = {
                'id': self.creator.id,
                'username': self.creator.username
            }
        
        return data


class CollectionItem(db.Model):
    """Collection item model (prompts in collections)"""
    __tablename__ = 'collection_items'
    
    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('prompt_collections.id'), nullable=False)
    prompt_id = db.Column(db.Integer, db.ForeignKey('writing_prompts.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    collection = relationship('PromptCollection', back_populates='collection_items')
    prompt = relationship('WritingPrompt')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('collection_id', 'prompt_id'),)


class UserTemplatePreference(db.Model):
    """User template preferences model"""
    __tablename__ = 'user_template_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('journal_templates.id'), nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)
    usage_frequency = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User')
    template = relationship('JournalTemplate')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'template_id'),)


class UserPromptPreference(db.Model):
    """User prompt preferences model"""
    __tablename__ = 'user_prompt_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prompt_id = db.Column(db.Integer, db.ForeignKey('writing_prompts.id'), nullable=False)
    is_favorite = db.Column(db.Boolean, default=False)
    difficulty_preference = db.Column(db.String(20))  # User's preferred difficulty
    category_preference = db.Column(db.String(50))  # User's preferred category
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User')
    prompt = relationship('WritingPrompt')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'prompt_id'),)
