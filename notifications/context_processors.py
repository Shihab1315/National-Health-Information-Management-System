# notifications/context_processors.py

from .models import Notification


def unread_notification_count(request):
    """
    Context processor to provide the unread notification count
    for the logged-in user.
    """
    if request.user.is_authenticated:
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return {'unread_notification_count': count}
    return {'unread_notification_count': 0}