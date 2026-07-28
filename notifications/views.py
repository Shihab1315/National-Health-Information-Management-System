from django.views.generic import ListView
from django.views.generic.edit import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from .models import Notification
from .forms import NotificationFilterForm
from .services import mark_as_read, mark_all_as_read, delete_notification
from django.contrib.auth.decorators import login_required
class NotificationCenterView(LoginRequiredMixin, ListView):
    """Display all notifications for the current user."""
    model = Notification
    template_name = 'notifications/notification_center.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        qs = Notification.objects.for_user(self.request.user)
        # Apply filters
        filter_type = self.request.GET.get('type')
        if filter_type:
            qs = qs.filter(notification_type=filter_type)
        status = self.request.GET.get('status')
        if status == 'unread':
            qs = qs.filter(is_read=False)
        elif status == 'read':
            qs = qs.filter(is_read=True)
        priority = self.request.GET.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(message__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = NotificationFilterForm(self.request.GET)
        context['total_unread'] = Notification.objects.unread_count(self.request.user)
        return context


def mark_as_read_ajax(request, pk):
    """AJAX endpoint to mark a notification as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    return JsonResponse({'status': 'ok'})


def mark_all_as_read_ajax(request):
    """AJAX endpoint to mark all notifications as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    Notification.objects.mark_all_as_read(request.user)
    return JsonResponse({'status': 'ok'})


def delete_notification_ajax(request, pk):
    """AJAX endpoint to delete a notification."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete()
    return JsonResponse({'status': 'ok'})


def delete_all_read_ajax(request):
    """AJAX endpoint to delete all read notifications."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    Notification.objects.filter(recipient=request.user, is_read=True).delete()
    return JsonResponse({'status': 'ok'})

@login_required
def unread_count(request):
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'count': count
    })