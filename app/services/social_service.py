from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import func, desc, and_, or_
from app import db
from app.models.entry import Entry
from app.models.user import User

def get_anonymous_public_entries(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """Get anonymous public entries for community feed."""
    entries = Entry.query.filter(
        and_(
            Entry.is_private == False,
            Entry.content != None,
            Entry.content != ''
        )
    ).order_by(Entry.created_at.desc()).offset(offset).limit(limit).all()
    
    public_entries = []
    for entry in entries:
        # Remove any identifying information
        safe_content = sanitize_content_for_sharing(entry.content)
        
        public_entries.append({
            'id': entry.id,
            'content': safe_content,
            'mood': entry.mood,
            'created_at': entry.created_at.isoformat(),
            'word_count': len(entry.content.split()) if entry.content else 0,
            'is_anonymous': True,
            'engagement': get_entry_engagement(entry.id)
        })
    
    return public_entries

def sanitize_content_for_sharing(content: str) -> str:
    """Remove personal information from content for public sharing."""
    import re
    
    # Remove common personal identifiers (basic implementation)
    # In production, you'd use more sophisticated NLP techniques
    patterns_to_remove = [
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # Dates
        r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b',  # Times
    ]
    
    sanitized = content
    for pattern in patterns_to_remove:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized)
    
    # Limit content length for public display
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + '...'
    
    return sanitized

def get_entry_engagement(entry_id: int) -> Dict[str, int]:
    """Get engagement metrics for an entry (likes, views, etc.)."""
    # For now, return mock data - in production, this would come from engagement tables
    return {
        'likes': 0,
        'views': 0,
        'comments': 0
    }

def share_entry_anonymously(entry_id: int, user_id: int) -> Dict[str, Any]:
    """Share an entry anonymously to the community."""
    entry = Entry.query.filter_by(id=entry_id, user_id=user_id).first()
    if not entry:
        return {'success': False, 'error': 'Entry not found'}
    
    if entry.is_private:
        return {'success': False, 'error': 'Private entries cannot be shared'}
    
    # In production, this would add to a shared_entries table
    # For now, we'll just return success
    return {
        'success': True,
        'message': 'Entry shared anonymously',
        'share_id': f"anon_{entry_id}_{datetime.utcnow().timestamp()}"
    }

def get_community_stats() -> Dict[str, Any]:
    """Get community-wide statistics."""
    total_entries = Entry.query.filter_by(is_private=False).count()
    total_users = User.query.count()
    
    # Active users in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_users = db.session.query(Entry.user_id).filter(
        Entry.created_at >= week_ago
    ).distinct().count()
    
    # Most common moods
    mood_stats = db.session.query(
        Entry.mood, func.count(Entry.id)
    ).filter(
        and_(
            Entry.mood.isnot(None),
            Entry.is_private == False
        )
    ).group_by(Entry.mood).order_by(desc(func.count(Entry.id))).limit(5).all()
    
    return {
        'total_entries': total_entries,
        'total_users': total_users,
        'active_users_week': active_users,
        'popular_moods': [{'mood': mood, 'count': count} for mood, count in mood_stats]
    }

def get_trending_topics(limit: int = 10) -> List[Dict[str, Any]]:
    """Get trending topics from public entries."""
    # Simple keyword extraction from public entries
    from collections import Counter
    import re
    
    entries = Entry.query.filter(
        and_(
            Entry.is_private == False,
            Entry.created_at >= datetime.utcnow() - timedelta(days=7)
        )
    ).all()
    
    # Extract keywords (simple implementation)
    all_words = []
    for entry in entries:
        if entry.content:
            # Remove common words and extract meaningful words
            words = re.findall(r'\b[a-zA-Z]{4,}\b', entry.content.lower())
            # Filter out common stop words
            stop_words = {'that', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'only'}
            words = [word for word in words if word not in stop_words]
            all_words.extend(words)
    
    word_counts = Counter(all_words)
    trending = [{'topic': word, 'count': count} for word, count in word_counts.most_common(limit)]
    
    return trending

def get_inspiration_prompts() -> List[str]:
    """Get writing inspiration prompts based on community trends."""
    base_prompts = [
        "What made you smile today?",
        "Describe a challenge you overcame recently",
        "What are you grateful for right now?",
        "Share a recent accomplishment",
        "What did you learn today?",
        "Describe your perfect day",
        "What's something that made you think differently?",
        "Share a moment of joy",
        "What are you looking forward to?",
        "Describe a person who inspires you"
    ]
    
    # Add trend-based prompts
    trending = get_trending_topics(3)
    trend_prompts = []
    for topic in trending:
        trend_prompts.append(f"Write about your thoughts on {topic['topic']}")
    
    return base_prompts + trend_prompts

def like_public_entry(entry_id: int, user_id: int) -> Dict[str, Any]:
    """Like a public entry."""
    # In production, this would add to an engagement table
    # For now, return mock response
    return {
        'success': True,
        'message': 'Entry liked',
        'total_likes': 1
    }

def report_public_entry(entry_id: int, user_id: int, reason: str) -> Dict[str, Any]:
    """Report a public entry for inappropriate content."""
    # In production, this would add to a moderation queue
    return {
        'success': True,
        'message': 'Entry reported for review'
    }

def get_user_privacy_settings(user_id: int) -> Dict[str, Any]:
    """Get user's privacy settings."""
    user = User.query.get(user_id)
    if not user:
        return {}
    
    return {
        'auto_share_anonymous': getattr(user, 'auto_share_anonymous', False),
        'allow_public_search': getattr(user, 'allow_public_search', False),
        'show_in_community': getattr(user, 'show_in_community', True),
        'default_privacy': getattr(user, 'default_privacy', True)
    }

def update_privacy_settings(user_id: int, settings: Dict[str, Any]) -> bool:
    """Update user's privacy settings."""
    user = User.query.get(user_id)
    if not user:
        return False
    
    try:
        user.auto_share_anonymous = settings.get('auto_share_anonymous', False)
        user.allow_public_search = settings.get('allow_public_search', False)
        user.show_in_community = settings.get('show_in_community', True)
        user.default_privacy = settings.get('default_privacy', True)
        
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
