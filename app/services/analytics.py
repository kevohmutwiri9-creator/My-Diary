from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, extract, cast, Date, text

from app import db
from app.models.entry import Entry
from app.models.user import User


def _get_date_expression():
    """Get the appropriate date expression for the current database dialect."""
    dialect = db.engine.dialect.name.lower()
    
    if dialect == 'mssql':
        # SQL Server: Use CONVERT(date, column)
        return func.cast(Entry.created_at, Date)
    elif dialect == 'postgresql':
        # PostgreSQL: Use DATE_TRUNC('day', column)
        return func.date_trunc('day', Entry.created_at)
    elif dialect == 'mysql':
        # MySQL: Use DATE(column)
        return func.date(Entry.created_at)
    else:
        # SQLite and others: Use DATE(column)
        return func.date(Entry.created_at)


def build_dashboard_analytics(user_id: int) -> Dict[str, Any]:
    """Assemble all analytics for the dashboard in a single call."""
    now = datetime.utcnow()
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found for analytics build")

    entries_query = Entry.query.filter(Entry.user_id == user_id)

    total_entries = entries_query.count()
    entries_this_month = _count_entries(entries_query, since=now - timedelta(days=30))
    entries_this_week = _count_entries(entries_query, since=now - timedelta(days=7))

    mood_rows = (
        db.session.query(Entry.mood, func.count(Entry.id))
        .filter(Entry.user_id == user_id, Entry.mood.isnot(None))
        .group_by(Entry.mood)
        .order_by(func.count(Entry.id).desc())
        .all()
    )
    mood_labels = [row[0] for row in mood_rows]
    mood_counts = [row[1] for row in mood_rows]
    most_common_mood = mood_labels[0] if mood_labels else None

    mood_chart = {"labels": mood_labels, "data": mood_counts}
    heatmap = _build_heatmap(entries_query, now)
    trend = _build_trend(entries_query, now)
    streaks = _build_streaks(user, entries_query, now)
    keywords = _build_keywords(entries_query)
    productivity = _build_productivity(entries_query, now)

    stats = {
        "total_entries": total_entries,
        "entries_this_month": entries_this_month,
        "entries_this_week": entries_this_week,
        "most_common_mood": most_common_mood,
    }

    return {
        "stats": stats,
        "mood_chart": mood_chart,
        "heatmap": heatmap,
        "trend": trend,
        "streaks": streaks,
        "keywords": keywords,
        "productivity": productivity,
    }


def _count_entries(query, *, since: Optional[datetime] = None) -> int:
    if since is None:
        return query.count()
    return query.filter(Entry.created_at >= since).count()


def _build_heatmap(query, now: datetime) -> Dict[str, Any]:
    start = now - timedelta(days=90)
    # Use database-agnostic date expression
    date_expr = _get_date_expression()
    rows = (
        query.filter(Entry.created_at >= start)
        .with_entities(date_expr.label("entry_date"), func.count(Entry.id))
        .group_by(date_expr)
        .order_by(date_expr)
        .all()
    )
    points = [{"date": _coerce_iso_date(row.entry_date), "count": row[1]} for row in rows]
    max_count = max((point["count"] for point in points), default=0)
    return {"points": points, "max": max_count}


def _build_trend(query, now: datetime) -> Dict[str, Any]:
    start = now - timedelta(days=30)
    # Use database-agnostic date expression
    date_expr = _get_date_expression()
    rows = (
        query.filter(Entry.created_at >= start)
        .with_entities(date_expr.label("entry_date"), func.count(Entry.id))
        .group_by(date_expr)
        .order_by(date_expr)
        .all()
    )
    labels = [_format_date_label(row.entry_date) for row in rows]
    counts = [row[1] for row in rows]
    dataset = {"label": "Entries", "data": counts}
    return {"labels": labels, "datasets": [dataset]}


def _build_streaks(user: User, query, now: datetime) -> Dict[str, Any]:
    current_streak = user.streak_count or 0
    best_streak = getattr(user, "best_streak", None)
    if best_streak is None:
        best_streak = current_streak
    entries_this_week = _count_entries(query, since=now - timedelta(days=7))
    entries_this_month = _count_entries(query, since=now - timedelta(days=30))
    return {
        "current": current_streak,
        "best": best_streak,
        "entries_this_week": entries_this_week,
        "entries_this_month": entries_this_month,
    }


def _build_keywords(query) -> Dict[str, Any]:
    recent_entries = (
        query.order_by(Entry.created_at.desc())
        .with_entities(Entry.content)
        .limit(30)
        .all()
    )
    keywords: Dict[str, int] = {}
    for (content,) in recent_entries:
        if not content:
            continue
        for word in content.split():
            token = word.strip().lower()
            if len(token) < 4:
                continue
            keywords[token] = keywords.get(token, 0) + 1
    items = sorted(
        ({"label": label, "count": count} for label, count in keywords.items()),
        key=lambda item: item["count"],
        reverse=True,
    )
    return {"source": "recent_entries", "items": items[:12]}


def _build_productivity(query, now: datetime) -> Dict[str, Any]:
    last_30_start = now - timedelta(days=30)
    # Use database-agnostic date expression
    date_expr = _get_date_expression()
    last_30_rows = (
        query.filter(Entry.created_at >= last_30_start)
        .with_entities(date_expr.label("entry_date"), func.count(Entry.id))
        .group_by(date_expr)
        .all()
    )
    active_days = len(last_30_rows)
    entries_last_30 = sum(row[1] for row in last_30_rows)
    avg_per_active_day = entries_last_30 / active_days if active_days else 0
    avg_per_day = entries_last_30 / 30
    consistency_percent = (active_days / 30) * 100

    return {
        "consistency_percent": round(consistency_percent, 2),
        "active_days_30": active_days,
        "last_30_days": 30,
        "entries_last_30": entries_last_30,
        "avg_entries_per_active_day": round(avg_per_active_day, 2),
        "avg_entries_per_day": round(avg_per_day, 2),
    }


def _coerce_iso_date(value: Any) -> str:
    parsed = _parse_date(value)
    if parsed:
        return parsed.date().isoformat()
    return str(value)


def _format_date_label(value: Any) -> str:
    parsed = _parse_date(value)
    if parsed:
        return parsed.strftime("%b %d")
    return str(value)


def _parse_date(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        for parser in (_try_fromisoformat, _try_ymd):
            parsed = parser(value)
            if parsed:
                return parsed
    return None


def _try_fromisoformat(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _try_ymd(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def get_enhanced_analytics(user_id: int) -> Dict[str, Any]:
    """Get enhanced analytics data for dashboard widgets."""
    from app.models import User
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return {}
    
    # Basic stats
    total_entries = Entry.query.filter_by(user_id=user_id).count()
    
    # Writing streak analysis
    streak_data = get_writing_streak_analysis(user_id)
    
    # Mood patterns
    mood_patterns = get_mood_patterns(user_id)
    
    # Writing habits
    writing_habits = get_writing_habits(user_id)
    
    # Personal growth insights
    growth_insights = get_growth_insights(user_id)
    
    # Keyword analysis
    keyword_analysis = get_keyword_analysis(user_id)
    
    # Time patterns
    time_patterns = get_time_patterns(user_id)
    
    return {
        'streak_data': streak_data,
        'mood_patterns': mood_patterns,
        'writing_habits': writing_habits,
        'growth_insights': growth_insights,
        'keyword_analysis': keyword_analysis,
        'time_patterns': time_patterns,
        'total_entries': total_entries
    }


def get_writing_streak_analysis(user_id: int) -> Dict[str, Any]:
    """Analyze writing streaks and consistency."""
    date_expr = _get_date_expression()
    
    # Get all entry dates
    entry_dates = db.session.query(
        date_expr.label('date')
    ).filter(
        Entry.user_id == user_id
    ).distinct().order_by(date_expr).all()
    
    if not entry_dates:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'total_days': 0,
            'consistency_percent': 0,
            'monthly_streaks': []
        }
    
    dates = [row.date for row in entry_dates]
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    # Calculate streaks
    for i in range(len(dates)):
        if i == 0 or (dates[i] - dates[i-1]).days == 1:
            temp_streak += 1
        else:
            temp_streak = 1
        
        longest_streak = max(longest_streak, temp_streak)
    
    # Current streak (from most recent date)
    today = datetime.utcnow().date()
    most_recent = dates[-1]
    
    if (today - most_recent).days <= 1:
        current_streak = temp_streak
    else:
        current_streak = 0
    
    # Consistency percentage (entries in last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    recent_entries = len([d for d in dates if d >= thirty_days_ago])
    consistency_percent = (recent_entries / 30) * 100
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'total_days': len(dates),
        'consistency_percent': round(consistency_percent, 1)
    }


def get_mood_patterns(user_id: int) -> Dict[str, Any]:
    """Analyze mood patterns over time."""
    # Get mood distribution
    mood_counts = db.session.query(
        Entry.mood,
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id,
        Entry.mood.isnot(None)
    ).group_by(Entry.mood).all()
    
    # Get mood trends (last 12 weeks)
    twelve_weeks_ago = datetime.utcnow() - timedelta(weeks=12)
    mood_trends = db.session.query(
        func.date_trunc('week', Entry.created_at).label('week'),
        Entry.mood,
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id,
        Entry.created_at >= twelve_weeks_ago,
        Entry.mood.isnot(None)
    ).group_by(
        func.date_trunc('week', Entry.created_at),
        Entry.mood
    ).order_by('week').all()
    
    # Process trends data
    trend_data = {}
    for week, mood, count in mood_trends:
        week_str = week.strftime('%Y-%m-%d')
        if week_str not in trend_data:
            trend_data[week_str] = {}
        trend_data[week_str][mood] = count
    
    return {
        'distribution': {mood: count for mood, count in mood_counts},
        'trends': trend_data,
        'most_common': max(mood_counts, key=lambda x: x[1])[0] if mood_counts else None
    }


def get_writing_habits(user_id: int) -> Dict[str, Any]:
    """Analyze writing habits and patterns."""
    # Word count statistics
    word_counts = [entry.word_count or 0 for entry in Entry.query.filter_by(user_id=user_id).all()]
    
    if not word_counts:
        return {
            'avg_words': 0,
            'total_words': 0,
            'longest_entry': 0,
            'preferred_time': None,
            'preferred_day': None
        }
    
    avg_words = sum(word_counts) / len(word_counts)
    total_words = sum(word_counts)
    longest_entry = max(word_counts)
    
    # Preferred writing time (hour of day)
    hour_counts = db.session.query(
        extract('hour', Entry.created_at).label('hour'),
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id
    ).group_by(extract('hour', Entry.created_at)).all()
    
    preferred_time = max(hour_counts, key=lambda x: x[1])[0] if hour_counts else None
    
    # Preferred writing day
    day_counts = db.session.query(
        extract('dow', Entry.created_at).label('day'),
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id
    ).group_by(extract('dow', Entry.created_at)).all()
    
    preferred_day = max(day_counts, key=lambda x: x[1])[0] if day_counts else None
    
    return {
        'avg_words': round(avg_words, 1),
        'total_words': total_words,
        'longest_entry': longest_entry,
        'preferred_time': int(preferred_time) if preferred_time else None,
        'preferred_day': int(preferred_day) if preferred_day else None
    }


def get_growth_insights(user_id: int) -> Dict[str, Any]:
    """Generate personal growth insights."""
    # Entry frequency over time
    monthly_counts = db.session.query(
        func.date_trunc('month', Entry.created_at).label('month'),
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id
    ).group_by(func.date_trunc('month', Entry.created_at)).all()
    
    # Calculate growth rate
    if len(monthly_counts) >= 2:
        recent = monthly_counts[-1][1]
        previous = monthly_counts[-2][1]
        growth_rate = ((recent - previous) / previous * 100) if previous > 0 else 0
    else:
        growth_rate = 0
    
    # Writing goals progress
    user = User.query.get(user_id)
    daily_goal = getattr(user, 'daily_goal', 1)
    weekly_goal = getattr(user, 'weekly_goal', 7)
    
    # Recent progress
    today = datetime.utcnow().date()
    today_entries = Entry.query.filter(
        Entry.user_id == user_id,
        func.date(Entry.created_at) == today
    ).count()
    
    week_start = today - timedelta(days=today.weekday())
    week_entries = Entry.query.filter(
        Entry.user_id == user_id,
        func.date(Entry.created_at) >= week_start
    ).count()
    
    return {
        'growth_rate': round(growth_rate, 1),
        'daily_progress': min(today_entries / daily_goal * 100, 100) if daily_goal > 0 else 0,
        'weekly_progress': min(week_entries / weekly_goal * 100, 100) if weekly_goal > 0 else 0,
        'monthly_trend': {str(month): count for month, count in monthly_counts}
    }


def get_keyword_analysis(user_id: int) -> Dict[str, Any]:
    """Analyze frequently used keywords and themes."""
    # Get recent entries for keyword analysis
    recent_entries = Entry.query.filter_by(user_id=user_id).order_by(Entry.created_at.desc()).limit(50).all()
    
    # Simple keyword extraction (common words)
    common_words = set(['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'])
    
    word_freq = {}
    for entry in recent_entries:
        if entry.content:
            words = entry.content.lower().split()
            for word in words:
                word = word.strip('.,!?;:"()[]{}')
                if len(word) > 3 and word not in common_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get top keywords
    top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    
    return {
        'top_keywords': [{'word': word, 'count': count} for word, count in top_keywords],
        'total_words_analyzed': sum(word_freq.values())
    }


def get_time_patterns(user_id: int) -> Dict[str, Any]:
    """Analyze time-based writing patterns."""
    # Hourly distribution
    hourly_dist = db.session.query(
        extract('hour', Entry.created_at).label('hour'),
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id
    ).group_by(extract('hour', Entry.created_at)).all()
    
    # Day of week distribution
    dow_dist = db.session.query(
        extract('dow', Entry.created_at).label('day'),
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id
    ).group_by(extract('dow', Entry.created_at)).all()
    
    # Monthly distribution
    monthly_dist = db.session.query(
        extract('month', Entry.created_at).label('month'),
        func.count(Entry.id).label('count')
    ).filter(
        Entry.user_id == user_id
    ).group_by(extract('month', Entry.created_at)).all()
    
    return {
        'hourly': {int(hour): count for hour, count in hourly_dist},
        'daily': {int(day): count for day, count in dow_dist},
        'monthly': {int(month): count for month, count in monthly_dist}
    }


def generate_word_cloud_data(user_id: int, limit: int = 50) -> Dict[str, Any]:
    """Generate word cloud data with weights and categories."""
    from collections import Counter
    import re
    
    # Get all entries
    entries = Entry.query.filter_by(user_id=user_id).all()
    
    if not entries:
        return {'words': [], 'categories': {}, 'total_words': 0}
    
    # Process all text
    all_text = ' '.join([entry.content for entry in entries if entry.content])
    
    # Clean and tokenize
    words = re.findall(r'\b[a-zA-Z]+\b', all_text.lower())
    
    # Filter out common words
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
        'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our',
        'their', 'a', 'an', 'what', 'when', 'where', 'why', 'how', 'who', 'which',
        'just', 'really', 'very', 'so', 'also', 'even', 'only', 'now', 'then', 'here',
        'there', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further',
        'than', 'once', 'more', 'most', 'some', 'such', 'no', 'nor', 'not', 'only',
        'own', 'same', 'so', 'than', 'too', 'very'
    }
    
    # Count meaningful words
    word_counts = Counter(word for word in words if len(word) > 3 and word not in stop_words)
    
    # Categorize words
    categories = {
        'emotions': {'happy', 'sad', 'angry', 'excited', 'joy', 'love', 'fear', 'worry', 'peace', 'calm', 'stress', 'anxiety', 'grateful', 'hope', 'dream', 'feel'},
        'activities': {'work', 'school', 'home', 'family', 'friends', 'meeting', 'class', 'project', 'exercise', 'walk', 'run', 'play', 'travel', 'visit', 'call', 'talk', 'read', 'write', 'cook', 'clean'},
        'time': {'today', 'yesterday', 'tomorrow', 'week', 'month', 'year', 'morning', 'evening', 'night', 'day', 'time', 'hour', 'minute', 'moment'},
        'relationships': {'mother', 'father', 'brother', 'sister', 'friend', 'husband', 'wife', 'son', 'daughter', 'team', 'boss', 'colleague'},
        'personal_growth': {'learn', 'grow', 'change', 'improve', 'better', 'goal', 'plan', 'future', 'dream', 'wish', 'hope', 'believe', 'think', 'understand'},
        'work_career': {'job', 'career', 'office', 'business', 'company', 'team', 'project', 'meeting', 'client', 'customer', 'sale', 'present', 'report'},
        'health_wellness': {'health', 'doctor', 'medicine', 'sleep', 'rest', 'food', 'eat', 'drink', 'water', 'exercise', 'gym', 'weight', 'body', 'mind'},
        'reflection': {'think', 'feel', 'know', 'realize', 'understand', 'remember', 'forget', 'decide', 'choose', 'want', 'need', 'like', 'hate'}
    }
    
    # Categorize words
    word_categories = {}
    for word, count in word_counts.most_common(limit):
        word_category = 'general'
        for category, category_words in categories.items():
            if word in category_words:
                word_category = category
                break
        word_categories[word] = word_category
    
    # Generate word cloud data
    max_count = max(word_counts.values()) if word_counts else 1
    
    word_cloud_data = []
    for word, count in word_counts.most_common(limit):
        # Calculate size (scale from 10 to 60)
        size = int(10 + (count / max_count) * 50)
        
        word_cloud_data.append({
            'text': word,
            'size': size,
            'weight': count,
            'category': word_categories.get(word, 'general'),
            'color': _get_category_color(word_categories.get(word, 'general'))
        })
    
    # Category distribution
    category_counts = Counter(word_categories.values())
    
    return {
        'words': word_cloud_data,
        'categories': dict(category_counts),
        'total_words': len(word_counts),
        'most_common': word_counts.most_common(1)[0] if word_counts else None
    }


def _get_category_color(category: str) -> str:
    """Get color for word category."""
    colors = {
        'emotions': '#e74c3c',
        'activities': '#3498db',
        'time': '#f39c12',
        'relationships': '#9b59b6',
        'personal_growth': '#2ecc71',
        'work_career': '#34495e',
        'health_wellness': '#16a085',
        'reflection': '#e67e22',
        'general': '#95a5a6'
    }
    return colors.get(category, '#95a5a6')


def get_advanced_patterns(user_id: int) -> Dict[str, Any]:
    """Get advanced writing patterns and insights."""
    from collections import defaultdict
    import statistics
    
    # Get entries with analysis
    entries = Entry.query.filter_by(user_id=user_id).order_by(Entry.created_at).all()
    
    if not entries:
        return {}
    
    # Sentiment trends
    sentiment_trends = []
    for entry in entries[-30:]:  # Last 30 entries
        if entry.content:
            # Simple sentiment analysis
            positive_words = ['happy', 'good', 'great', 'love', 'excellent', 'wonderful', 'amazing', 'fantastic']
            negative_words = ['sad', 'bad', 'terrible', 'hate', 'awful', 'horrible', 'disappointed', 'frustrated']
            
            words = entry.content.lower().split()
            positive_count = sum(1 for word in words if any(pos in word for pos in positive_words))
            negative_count = sum(1 for word in words if any(neg in word for neg in negative_words))
            
            sentiment = 0
            if positive_count > negative_count:
                sentiment = 1
            elif negative_count > positive_count:
                sentiment = -1
                
            sentiment_trends.append({
                'date': entry.created_at.isoformat(),
                'sentiment': sentiment,
                'word_count': len(words)
            })
    
    # Writing complexity
    sentence_lengths = []
    avg_word_lengths = []
    
    for entry in entries:
        if entry.content:
            sentences = entry.content.split('.')
            for sentence in sentences:
                if sentence.strip():
                    words = sentence.split()
                    sentence_lengths.append(len(words))
                    if words:
                        avg_word_lengths.append(statistics.mean(len(word) for word in words))
    
    # Topic modeling (simple keyword clustering)
    topic_keywords = defaultdict(list)
    for entry in entries:
        if entry.content:
            words = entry.content.lower().split()
            for word in words:
                if len(word) > 5:  # Focus on meaningful words
                    topic_keywords[word].append(entry.created_at)
    
    # Find trending topics
    trending_topics = []
    for word, dates in topic_keywords.items():
        if len(dates) >= 3:  # Words mentioned at least 3 times
            recent_count = len([date for date in dates if date > datetime.now() - timedelta(days=30)])
            if recent_count >= 2:  # Trending recently
                trending_topics.append({
                    'topic': word,
                    'frequency': len(dates),
                    'recent_frequency': recent_count
                })
    
    trending_topics.sort(key=lambda x: x['recent_frequency'], reverse=True)
    
    return {
        'sentiment_trends': sentiment_trends,
        'writing_complexity': {
            'avg_sentence_length': statistics.mean(sentence_lengths) if sentence_lengths else 0,
            'avg_word_length': statistics.mean(avg_word_lengths) if avg_word_lengths else 0,
            'sentence_length_variance': statistics.variance(sentence_lengths) if len(sentence_lengths) > 1 else 0
        },
        'trending_topics': trending_topics[:10],
        'writing_consistency': _calculate_writing_consistency(entries)
    }


def _calculate_writing_consistency(entries) -> Dict[str, Any]:
    """Calculate writing consistency metrics."""
    if len(entries) < 2:
        return {'score': 0, 'pattern': 'insufficient_data'}
    
    # Group entries by day
    daily_entries = defaultdict(list)
    for entry in entries:
        day = entry.created_at.date()
        daily_entries[day].append(entry)
    
    # Calculate consistency score
    total_days = (entries[-1].created_at.date() - entries[0].created_at.date()).days + 1
    writing_days = len(daily_entries)
    
    consistency_score = (writing_days / total_days) * 100
    
    # Identify pattern
    if consistency_score >= 80:
        pattern = 'daily_writer'
    elif consistency_score >= 60:
        pattern = 'frequent_writer'
    elif consistency_score >= 40:
        pattern = 'regular_writer'
    elif consistency_score >= 20:
        pattern = 'occasional_writer'
    else:
        pattern = 'sporadic_writer'
    
    return {
        'score': round(consistency_score, 1),
        'pattern': pattern,
        'total_days': total_days,
        'writing_days': writing_days,
        'avg_entries_per_writing_day': sum(len(day_entries) for day_entries in daily_entries.values()) / writing_days if writing_days > 0 else 0
    }


def get_emotional_journey(user_id: int) -> Dict[str, Any]:
    """Map emotional journey over time."""
    from app.services.ai_sentiment import sentiment_analyzer
    
    entries = Entry.query.filter_by(user_id=user_id).order_by(Entry.created_at).all()
    
    if not entries:
        return {}
    
    emotional_journey = []
    mood_progression = []
    
    for entry in entries:
        if entry.content:
            # Analyze sentiment
            analysis = sentiment_analyzer.analyze_sentiment(entry.content)
            
            emotional_journey.append({
                'date': entry.created_at.isoformat(),
                'sentiment': analysis['sentiment'],
                'confidence': analysis['confidence'],
                'mood': entry.mood,
                'title': entry.title or 'Untitled'
            })
            
            if entry.mood:
                mood_progression.append({
                    'date': entry.created_at.isoformat(),
                    'mood': entry.mood
                })
    
    # Find emotional patterns
    positive_periods = []
    negative_periods = []
    
    current_positive = None
    current_negative = None
    
    for point in emotional_journey:
        if point['sentiment'] == 'positive':
            if current_positive is None:
                current_positive = {'start': point['date'], 'entries': 1}
            else:
                current_positive['entries'] += 1
            current_negative = None
        elif point['sentiment'] == 'negative':
            if current_negative is None:
                current_negative = {'start': point['date'], 'entries': 1}
            else:
                current_negative['entries'] += 1
            current_positive = None
        else:
            if current_positive:
                current_positive['end'] = point['date']
                positive_periods.append(current_positive)
                current_positive = None
            if current_negative:
                current_negative['end'] = point['date']
                negative_periods.append(current_negative)
                current_negative = None
    
    # Close any open periods
    if current_positive:
        positive_periods.append(current_positive)
    if current_negative:
        negative_periods.append(current_negative)
    
    return {
        'journey': emotional_journey,
        'mood_progression': mood_progression,
        'positive_periods': positive_periods,
        'negative_periods': negative_periods,
        'emotional_resilience': _calculate_emotional_resilience(emotional_journey)
    }


def _calculate_emotional_resilience(journey) -> Dict[str, Any]:
    """Calculate emotional resilience metrics."""
    if len(journey) < 5:
        return {'score': 0, 'recovery_time': 0}
    
    # Find negative to positive transitions
    recovery_times = []
    negative_start = None
    
    for i, point in enumerate(journey):
        if point['sentiment'] == 'negative' and negative_start is None:
            negative_start = i
        elif point['sentiment'] == 'positive' and negative_start is not None:
            recovery_time = i - negative_start
            recovery_times.append(recovery_time)
            negative_start = None
    
    avg_recovery = sum(recovery_times) / len(recovery_times) if recovery_times else 0
    
    # Calculate resilience score (lower recovery time = higher resilience)
    max_recovery = max(recovery_times) if recovery_times else 1
    resilience_score = (1 - (avg_recovery / max_recovery)) * 100 if recovery_times else 50
    
    return {
        'score': round(resilience_score, 1),
        'avg_recovery_time': round(avg_recovery, 1),
        'total_recoveries': len(recovery_times),
        'resilience_level': _get_resilience_level(resilience_score)
    }


def _get_resilience_level(score: float) -> str:
    """Get resilience level based on score."""
    if score >= 80:
        return 'very_high'
    elif score >= 60:
        return 'high'
    elif score >= 40:
        return 'moderate'
    elif score >= 20:
        return 'low'
    else:
        return 'very_low'
