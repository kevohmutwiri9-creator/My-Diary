import re
from datetime import datetime
from app import db


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip('-')


entry_tags = db.Table(
    'entry_tags',
    db.Column('entry_id', db.Integer, db.ForeignKey('entries.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(64), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entries = db.relationship(
        'Entry',
        secondary=entry_tags,
        back_populates='tags'
    )

    def __init__(self, name: str, **kwargs):
        normalized = name.strip()
        if not normalized:
            raise ValueError('Tag name cannot be empty')
        kwargs.setdefault('name', normalized)
        kwargs.setdefault('slug', _slugify(normalized))
        super().__init__(**kwargs)

    @staticmethod
    def normalize(name: str) -> str:
        return name.strip()

    @staticmethod
    def slug_for(name: str) -> str:
        return _slugify(name)

    def __repr__(self):
        return f"<Tag {self.name}>"
