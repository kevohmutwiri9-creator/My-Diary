from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from sqlalchemy import func, extract
from app import db
from app.models.entry import Entry
from app.models.user import User

def get_user_productivity_stats(user_id: int) -> Dict[str, Any]:
    """Get comprehensive productivity statistics for a user."""
    user = User.query.get(user_id)
    if not user:
        return {}
    
    now = datetime.utcnow()
    entries_query = Entry.query.filter_by(user_id=user_id)
    
    # Basic stats
    total_entries = entries_query.count()
    
    # Last 30 days activity
    last_30_start = now - timedelta(days=30)
    recent_entries = entries_query.filter(Entry.created_at >= last_30_start).count()
    
    # Current streak
    current_streak = calculate_current_streak(user_id)
    
    # Longest streak
    longest_streak = calculate_longest_streak(user_id)
    
    # Writing patterns
    writing_patterns = analyze_writing_patterns(user_id)
    
    # Goal progress
    goal_progress = get_goal_progress(user_id)
    
    # Mood trends
    mood_trends = analyze_mood_trends(user_id)
    
    return {
        'total_entries': total_entries,
        'recent_entries': recent_entries,
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'writing_patterns': writing_patterns,
        'goal_progress': goal_progress,
        'mood_trends': mood_trends,
        'productivity_score': calculate_productivity_score(user_id)
    }

def calculate_current_streak(user_id: int) -> int:
    """Calculate current journaling streak."""
    user = User.query.get(user_id)
    return user.streak_count or 0

def calculate_longest_streak(user_id: int) -> int:
    """Calculate the longest streak in user's history."""
    entries = Entry.query.filter_by(user_id=user_id).order_by(Entry.created_at.asc()).all()
    
    if not entries:
        return 0
    
    longest_streak = 0
    current_streak = 0
    
    # Group entries by date
    entry_dates = set()
    for entry in entries:
        entry_dates.add(entry.created_at.date())
    
    # Check consecutive days
    today = datetime.utcnow().date()
    check_date = today
    
    while check_date in entry_dates:
        current_streak += 1
        longest_streak = max(longest_streak, current_streak)
        check_date -= timedelta(days=1)
    
    return longest_streak

def analyze_writing_patterns(user_id: int) -> Dict[str, Any]:
    """Analyze user's writing patterns."""
    entries = Entry.query.filter_by(user_id=user_id).all()
    
    if not entries:
        return {}
    
    # Time of day analysis
    hour_counts = {}
    day_of_week_counts = {}
    word_counts = []
    
    for entry in entries:
        # Time of day
        hour = entry.created_at.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Day of week
        day_of_week = entry.created_at.strftime('%A')
        day_of_week_counts[day_of_week] = day_of_week_counts.get(day_of_week, 0) + 1
        
        # Word count
        if entry.content:
            word_count = len(entry.content.split())
            word_counts.append(word_count)
    
    # Find most productive time
    most_productive_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None
    most_productive_day = max(day_of_week_counts, key=day_of_week_counts.get) if day_of_week_counts else None
    
    # Average word count
    avg_word_count = sum(word_counts) / len(word_counts) if word_counts else 0
    
    return {
        'most_productive_hour': most_productive_hour,
        'most_productive_day': most_productive_day,
        'avg_word_count': round(avg_word_count, 1),
        'total_words_written': sum(word_counts),
        'hour_distribution': hour_counts,
        'day_distribution': day_of_week_counts
    }

def get_goal_progress(user_id: int) -> Dict[str, Any]:
    """Get progress towards user's writing goals."""
    user = User.query.get(user_id)
    if not user:
        return {}
    
    # Default goals
    daily_goal = getattr(user, 'daily_goal', 1)  # entries per day
    weekly_goal = getattr(user, 'weekly_goal', 7)  # entries per week
    
    now = datetime.utcnow()
    
    # Daily progress
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_entries = Entry.query.filter(
        Entry.user_id == user_id,
        Entry.created_at >= today_start
    ).count()
    
    daily_progress = min(today_entries / daily_goal, 1.0) if daily_goal and daily_goal > 0 else 0
    
    # Weekly progress
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_entries = Entry.query.filter(
        Entry.user_id == user_id,
        Entry.created_at >= week_start
    ).count()
    
    weekly_progress = min(week_entries / weekly_goal, 1.0) if weekly_goal and weekly_goal > 0 else 0
    
    return {
        'daily_goal': daily_goal,
        'weekly_goal': weekly_goal,
        'daily_progress': round(daily_progress, 2),
        'weekly_progress': round(weekly_progress, 2),
        'today_entries': today_entries,
        'week_entries': week_entries
    }

def analyze_mood_trends(user_id: int) -> Dict[str, Any]:
    """Analyze mood trends over time."""
    entries = Entry.query.filter_by(user_id=user_id).filter(Entry.mood.isnot(None)).all()
    
    if not entries:
        return {}
    
    mood_counts = {}
    recent_moods = []
    
    for entry in entries:
        mood = entry.mood
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        # Get recent moods (last 10 entries)
        if len(recent_moods) < 10:
            recent_moods.append(mood)
    
    # Most common mood
    most_common_mood = max(mood_counts, key=mood_counts.get) if mood_counts else None
    
    return {
        'most_common_mood': most_common_mood,
        'mood_distribution': mood_counts,
        'recent_moods': recent_moods,
        'total_mooded_entries': len(entries)
    }

def calculate_productivity_score(user_id: int) -> int:
    """Calculate overall productivity score (0-100)."""
    user = User.query.get(user_id)
    if not user:
        return 0
    
    now = datetime.utcnow()
    entries_query = Entry.query.filter_by(user_id=user_id)
    
    # Get basic stats without calling get_user_productivity_stats to avoid recursion
    total_entries = entries_query.count()
    last_30_start = now - timedelta(days=30)
    recent_entries = entries_query.filter(Entry.created_at >= last_30_start).count()
    current_streak = calculate_current_streak(user_id)
    
    # Writing patterns
    writing_patterns = analyze_writing_patterns(user_id)
    
    # Goal progress
    goal_progress = get_goal_progress(user_id)
    
    score = 0
    
    # Consistency score (40%)
    consistency_score = min(current_streak * 5, 40)
    score += consistency_score
    
    # Volume score (30%)
    volume_score = min(recent_entries * 2, 30)
    score += volume_score
    
    # Quality score (20%)
    quality_score = min(writing_patterns.get('avg_word_count', 0) / 10, 20)
    score += quality_score
    
    # Goal achievement score (10%)
    goal_score = goal_progress.get('daily_progress', 0) * 10
    score += goal_score
    
    return min(int(score), 100)

def get_productivity_recommendations(user_id: int) -> List[str]:
    """Get personalized productivity recommendations."""
    stats = get_user_productivity_stats(user_id)
    recommendations = []
    
    if not stats:
        return ["Start writing to build your journaling habit!"]
    
    # Streak recommendations
    if stats['current_streak'] == 0:
        recommendations.append("Start with one entry today to build your streak!")
    elif stats['current_streak'] < 7:
        recommendations.append(f"Great start! Keep going for a full week to build a strong habit.")
    
    # Consistency recommendations
    if stats['recent_entries'] < 10:
        recommendations.append("Try writing more frequently to build consistency.")
    
    # Time-based recommendations
    patterns = stats['writing_patterns']
    if patterns.get('most_productive_hour'):
        hour = patterns['most_productive_hour']
        recommendations.append(f"You write best around {hour}:00. Schedule your journaling time then!")
    
    # Goal recommendations
    goals = stats['goal_progress']
    if goals.get('daily_progress', 0) < 1:
        recommendations.append("You're close to your daily goal! Write one more entry.")
    
    # Mood recommendations
    if stats['mood_trends'].get('most_common_mood'):
        mood = stats['mood_trends']['most_common_mood']
        recommendations.append(f"Track your {mood} feelings to understand patterns better.")
    
    return recommendations

def generate_calendar_events(user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
    """Generate calendar events for dashboard calendar view."""
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    entries = Entry.query.filter(
        Entry.user_id == user_id,
        Entry.created_at >= start_date,
        Entry.created_at <= end_date
    ).all()
    
    events = []
    for entry in entries:
        events.append({
            'date': entry.created_at.date().isoformat(),
            'title': entry.title or 'Journal Entry',
            'mood': entry.mood,
            'entry_id': entry.id,
            'word_count': len(entry.content.split()) if entry.content else 0
        })
    
    return events

def update_user_goals(user_id: int, daily_goal: int = None, weekly_goal: int = None) -> bool:
    """Update user's writing goals."""
    user = User.query.get(user_id)
    if not user:
        return False
    
    try:
        if daily_goal is not None:
            user.daily_goal = daily_goal
        if weekly_goal is not None:
            user.weekly_goal = weekly_goal
        
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
