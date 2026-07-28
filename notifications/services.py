from django.db.models import QuerySet
from .models import Notification


def mark_as_read(notification: Notification) -> Notification:
    """Mark a single notification as read."""
    notification.mark_as_read()
    return notification


def mark_all_as_read(user) -> int:
    """Mark all notifications for a user as read."""
    return Notification.objects.mark_all_as_read(user)


def delete_notification(notification: Notification) -> None:
    """Delete a notification."""
    notification.delete()


def delete_all_read(user) -> int:
    """Delete all read notifications for a user."""
    count, _ = Notification.objects.filter(recipient=user, is_read=True).delete()
    return count