from datetime import datetime
from app import db

class Media(db.Model):
    __tablename__ = 'media'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey('entries.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    filesize = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('media', lazy=True))
    entry = db.relationship('Entry', backref=db.backref('attachments', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'filetype': self.filetype,
            'filesize': self.filesize,
            'created_at': self.created_at.isoformat(),
            'url': f'/uploads/{self.filename}'
        }
