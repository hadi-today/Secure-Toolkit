# File: utils.py

from datetime import datetime, timezone

def humanize_time(dt_str):
    """Converts an ISO format datetime string to a human-readable relative time."""
    if not dt_str:
        return "somewhat recently"
    
    try:
        # Convert string from DB to an aware datetime object
        article_dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return dt_str # Return original string if format is unexpected

    now = datetime.now(timezone.utc)
    delta = now - article_dt

    seconds = delta.total_seconds()
    days = delta.days
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)

    if days > 1:
        return f"{days}d ago"
    if days == 1:
        return "1d ago"
    if hours > 0:
        return f"{hours}h ago"
    if minutes > 0:
        return f"{minutes}m ago"
    return f"{int(seconds)}s ago"