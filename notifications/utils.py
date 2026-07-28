from datetime import datetime
from django.utils import timezone


def time_ago(dt: datetime) -> str:
    """Return a human‑readable string representing the time since dt."""
    if not dt:
        return ""

    now = timezone.now()
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} min{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 172800:
        return "Yesterday"
    else:
        days = int(seconds // 86400)
        return f"{days} days ago"