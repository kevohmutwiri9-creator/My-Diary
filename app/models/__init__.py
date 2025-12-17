from app.models.user import User
from app.models.entry import Entry
from app.models.tag import Tag
from app.models.goal import Goal

# This makes the models available when importing from app.models
__all__ = ['User', 'Entry', 'Tag', 'Goal']
