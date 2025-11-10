from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app import db
from app.models.entry import Entry
from app.models.user import User


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
    rows = (
        query.filter(Entry.created_at >= start)
        .with_entities(func.date(Entry.created_at).label("entry_date"), func.count(Entry.id))
        .group_by("entry_date")
        .order_by("entry_date")
        .all()
    )
    points = [{"date": _coerce_iso_date(row.entry_date), "count": row[1]} for row in rows]
    max_count = max((point["count"] for point in points), default=0)
    return {"points": points, "max": max_count}


def _build_trend(query, now: datetime) -> Dict[str, Any]:
    start = now - timedelta(days=30)
    rows = (
        query.filter(Entry.created_at >= start)
        .with_entities(func.date(Entry.created_at).label("entry_date"), func.count(Entry.id))
        .group_by("entry_date")
        .order_by("entry_date")
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
    last_30_rows = (
        query.filter(Entry.created_at >= last_30_start)
        .with_entities(func.date(Entry.created_at).label("entry_date"), func.count(Entry.id))
        .group_by("entry_date")
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
