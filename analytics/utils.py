"""
Utility functions for the analytics app.
These are helper functions used across multiple modules.
"""

from datetime import datetime, timedelta
from django.utils import timezone
from typing import List, Dict, Any, Optional
from .constants import CHART_COLORS


def get_date_range_for_charts(days_back: int = 180) -> tuple:
    """
    Return a tuple of (start_date, end_date) for chart data.
    Default: last 6 months.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date


def format_date_for_chart(date_obj: datetime) -> str:
    """
    Format a datetime object for chart labels (e.g., 'Jan 2025').
    """
    return date_obj.strftime('%b %Y')


def get_chart_colors(count: int) -> List[str]:
    """
    Return a list of colors for charts, cycling through the color palette.
    """
    colors = list(CHART_COLORS.values())
    if count <= len(colors):
        return colors[:count]
    # If more colors needed, repeat the palette
    return (colors * (count // len(colors) + 1))[:count]


def get_status_color(status: str) -> str:
    """
    Map a status string to a CSS color class or hex color.
    """
    from .constants import STATUS_COLORS
    return STATUS_COLORS.get(status, 'gray')


def cache_key(*args, **kwargs) -> str:
    """
    Generate a consistent cache key from arguments.
    Useful for building cache keys dynamically.
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    return "analytics:" + ":".join(key_parts)


def is_within_last_days(dt: datetime, days: int) -> bool:
    """
    Check if a datetime is within the last N days.
    """
    if not dt:
        return False
    cutoff = timezone.now() - timedelta(days=days)
    return dt >= cutoff


def truncate_text(text: str, length: int = 50) -> str:
    """
    Truncate a string to a maximum length, adding ellipsis if needed.
    """
    if not text:
        return ''
    if len(text) <= length:
        return text
    return text[:length] + '...'


def safe_getattr(obj, attr, default=None):
    """
    Safely get an attribute from an object, returning default if it doesn't exist.
    """
    try:
        return getattr(obj, attr, default)
    except AttributeError:
        return default


def parse_search_query(query: str) -> List[str]:
    """
    Split a search query into a list of keywords.
    """
    if not query:
        return []
    return [part.strip() for part in query.split() if part.strip()]