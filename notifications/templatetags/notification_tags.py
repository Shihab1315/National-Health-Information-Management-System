from django import template
from django.db.models import Count
from ..models import Notification

register = template.Library()

@register.simple_tag
def unread_notifications_count(user):
    """Return the number of unread notifications for the user."""
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.unread_count(user)