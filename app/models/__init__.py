from app.models.user import User
from app.models.entry import Entry
from app.models.tag import Tag
from app.models.audit_log import AuditLog
from app.models.templates import JournalTemplate, WritingPrompt, PromptCollection, TemplateRating, PromptRating, PromptResponse
from app.models.media import Media
from app.models.template import EntryTemplate

# Try to import Goal model with error handling
try:
    from app.models.goal import Goal
    _GOAL_AVAILABLE = True
except ImportError:
    Goal = None
    _GOAL_AVAILABLE = False

# This makes the models available when importing from app.models
_available_models = ['User', 'Entry', 'Tag', 'AuditLog', 'JournalTemplate', 'WritingPrompt', 'PromptCollection', 'TemplateRating', 'PromptRating', 'PromptResponse', 'Media', 'EntryTemplate']
if _GOAL_AVAILABLE:
    _available_models.append('Goal')

__all__ = _available_models
