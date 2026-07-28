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

from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from accounts.decorators import role_required
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
    
@login_required
@role_required(['patient'])
def patient_notification_list(request):
    """
    Patient-specific notification list.
    Shows only the logged-in patient's own notifications.
    """
    user = request.user

    # Base queryset – only this user's notifications
    base_qs = Notification.objects.for_user(user)

    # ---------- Summary Cards ----------
    total = base_qs.count()
    unread = base_qs.filter(is_read=False).count()
    read = base_qs.filter(is_read=True).count()
    today = base_qs.filter(created_at__date=timezone.now().date()).count()

    # ---------- Search ----------
    search = request.GET.get('search', '')
    if search:
        base_qs = base_qs.filter(
            Q(title__icontains=search) |
            Q(message__icontains=search) |
            Q(notification_type__icontains=search)
        )

    # ---------- Filter ----------
    status_filter = request.GET.get('status', '')
    if status_filter == 'unread':
        base_qs = base_qs.filter(is_read=False)
    elif status_filter == 'read':
        base_qs = base_qs.filter(is_read=True)

    type_filter = request.GET.get('type', '')
    if type_filter:
        base_qs = base_qs.filter(notification_type=type_filter)

    # ---------- Sorting ----------
    sort = request.GET.get('sort', '-created_at')
    if sort == 'created_at':
        base_qs = base_qs.order_by('created_at')
    else:
        base_qs = base_qs.order_by('-created_at')

    # ---------- Pagination ----------
    paginator = Paginator(base_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ---------- Notification type choices for filter ----------
    type_choices = Notification.NotificationType.choices

    # ---------- Context ----------
    context = {
        'page_obj': page_obj,
        'notifications': page_obj,
        'total': total,
        'unread': unread,
        'read': read,
        'today': today,
        'search': search,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'sort': sort,
        'type_choices': type_choices,
        'user': user,
        'current_date': timezone.now(),
    }
    return render(request, 'notifications/patient/notification_list.html', context)

@login_required
@role_required(['patient'])
def patient_notification_detail(request, pk):
    """
    Detail view for a single notification.
    Automatically marks the notification as read when viewed.
    """
    notification = get_object_or_404(
        Notification.objects.select_related('sender'),
        pk=pk,
        recipient=request.user
    )

    # Auto-mark as read
    if not notification.is_read:
        notification.mark_as_read()

    context = {
        'notification': notification,
        'current_date': timezone.now(),
    }
    return render(request, 'notifications/patient/notification_detail.html', context)


@login_required
@role_required(['patient'])
def patient_notification_mark_read(request, pk):
    """Mark a notification as read (AJAX or POST)."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if request.method == 'POST':
        notification.mark_as_read()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'is_read': True})
        messages.success(request, 'Notification marked as read.')
    return redirect('notifications:patient_notification_detail', pk=pk)


@login_required
@role_required(['patient'])
def patient_notification_mark_unread(request, pk):
    """Mark a notification as unread (AJAX or POST)."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if request.method == 'POST':
        notification.is_read = False
        notification.save(update_fields=['is_read'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'is_read': False})
        messages.success(request, 'Notification marked as unread.')
    return redirect('notifications:patient_notification_detail', pk=pk)


@login_required
@role_required(['patient'])
def patient_notification_delete(request, pk):
    """Delete a notification (POST only)."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if request.method == 'POST':
        notification.delete()
        messages.success(request, 'Notification deleted.')
        return redirect('notifications:patient_notification_list')
    return redirect('notifications:patient_notification_detail', pk=pk)