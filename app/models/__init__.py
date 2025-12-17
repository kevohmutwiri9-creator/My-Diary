from app.models.user import User
from app.models.entry import Entry
from app.models.tag import Tag
from app.models.goal import Goal
from app.models.audit_log import AuditLog
from app.models.templates import JournalTemplate, WritingPrompt, PromptCollection, TemplateRating, PromptRating, PromptResponse
from app.models.media import Media
from app.models.template import EntryTemplate

# This makes the models available when importing from app.models
__all__ = ['User', 'Entry', 'Tag', 'Goal', 'AuditLog', 'JournalTemplate', 'WritingPrompt', 'PromptCollection', 'TemplateRating', 'PromptRating', 'PromptResponse', 'Media', 'EntryTemplate']
