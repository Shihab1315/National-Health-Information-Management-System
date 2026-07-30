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
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from doctors.models import Doctor
from django.views import View

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

@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorNotificationListView(View):
    """
    Doctor Notification List View.
    Displays all notifications for the logged-in doctor.
    """
    template_name = 'notifications/doctor/my_notifications.html'
    
    def get(self, request):
        try:
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "You are not registered as a doctor.")
            return redirect('dashboard:doctor_dashboard')
        
        # ✅ আপনার মডেল অনুযায়ী filter করুন
        notifications = Notification.objects.filter(
            recipient=request.user  # 'user' না হয়ে 'recipient' ব্যবহার করুন
        ).select_related('sender')
        
        # ========== SUMMARY STATISTICS ==========
        total = notifications.count()
        unread = notifications.filter(is_read=False).count()
        read = notifications.filter(is_read=True).count()
        today = notifications.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        # ========== SEARCH ==========
        search_query = request.GET.get('search', '').strip()
        if search_query:
            notifications = notifications.filter(
                Q(title__icontains=search_query) |
                Q(message__icontains=search_query)
            )
        
        # ========== FILTERS ==========
        status_filter = request.GET.get('status')
        if status_filter == 'unread':
            notifications = notifications.filter(is_read=False)
        elif status_filter == 'read':
            notifications = notifications.filter(is_read=True)
        
        category_filter = request.GET.get('category')
        if category_filter and category_filter != 'all':
            # আপনার মডেলে 'category' বা 'notification_type' চেক করুন
            if hasattr(Notification, 'category'):
                notifications = notifications.filter(category=category_filter)
            elif hasattr(Notification, 'notification_type'):
                notifications = notifications.filter(notification_type=category_filter)
        
        date_filter = request.GET.get('date_filter')
        if date_filter == 'today':
            notifications = notifications.filter(created_at__date=timezone.now().date())
        elif date_filter == 'this_week':
            start = timezone.now().date() - timedelta(days=timezone.now().weekday())
            end = start + timedelta(days=6)
            notifications = notifications.filter(created_at__date__range=[start, end])
        elif date_filter == 'this_month':
            start = timezone.now().date().replace(day=1)
            notifications = notifications.filter(created_at__date__gte=start)
        
        # ========== SORTING ==========
        sort_by = request.GET.get('sort', 'newest')
        sort_mapping = {
            'newest': '-created_at',
            'oldest': 'created_at',
            'unread_first': '-is_read',
        }
        order_by = sort_mapping.get(sort_by, '-created_at')
        notifications = notifications.order_by(order_by)
        
        # ========== PAGINATION ==========
        paginator = Paginator(notifications, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'doctor': doctor,
            'page_obj': page_obj,
            'notifications': page_obj,
            'total_notifications': total,
            'unread_notifications': unread,
            'read_notifications': read,
            'today_notifications': today,
            'search_query': search_query,
            'status_filter': status_filter,
            'category_filter': category_filter,
            'date_filter': date_filter,
            'sort_by': sort_by,
            'today': timezone.now().date(),
        }
        
        return render(request, self.template_name, context)
    
@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorNotificationMarkReadView(View):
    """
    Doctor Notification Mark as Read View.
    Marks a single notification as read (POST only).
    """
    
    def post(self, request, pk):
        # Get the logged-in doctor
        try:
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "You are not registered as a doctor.")
            return redirect('dashboard:doctor_dashboard')
        
        # Get the notification - only if it belongs to this user
        notification = get_object_or_404(
            Notification.objects.select_related('recipient', 'sender'),
            pk=pk,
            recipient=request.user
        )
        
        # Check if already read
        if notification.is_read:
            messages.info(request, "Notification is already marked as read.")
        else:
            # Mark as read
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
            messages.success(request, "✅ Notification marked as read.")
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Notification marked as read.' if not notification.is_read else 'Already read.',
                'is_read': notification.is_read,
                'read_at': notification.read_at.strftime('%Y-%m-%d %H:%M:%S') if notification.read_at else None,
            })
        
        # Redirect based on referer
        referer = request.META.get('HTTP_REFERER')
        if referer and 'notification_detail' in referer:
            return redirect('notifications:doctor_notification_detail', pk=notification.pk)
        else:
            return redirect('notifications:doctor_notifications')


@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorMarkAllNotificationsReadView(View):
    """
    Doctor Mark All Notifications as Read View.
    Marks all unread notifications as read for the logged-in user (POST only).
    """
    
    def post(self, request):
        # Get the logged-in doctor
        try:
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "You are not registered as a doctor.")
            return redirect('dashboard:doctor_dashboard')
        
        # Get count of unread notifications
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        if unread_count == 0:
            messages.info(request, "All notifications are already read.")
            return redirect('notifications:doctor_notifications')
        
        # ✅ Bulk update - efficient single query
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Success message
        messages.success(
            request, 
            f"✅ All {updated_count} notifications have been marked as read."
        )
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'All {updated_count} notifications marked as read.',
                'updated_count': updated_count,
            })
        
        return redirect('notifications:doctor_notifications')


@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorNotificationDetailView(View):
    """
    Doctor Notification Detail View.
    Displays complete notification details and auto-marks as read.
    """
    template_name = 'notifications/doctor/notification_detail.html'
    
    def get(self, request, pk):
        # Get the logged-in doctor
        try:
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "You are not registered as a doctor.")
            return redirect('dashboard:doctor_dashboard')
        
        # Get the notification - only if it belongs to this user
        notification = get_object_or_404(
            Notification.objects.select_related('recipient', 'sender'),
            pk=pk,
            recipient=request.user
        )
        
        # Auto-mark as read if unread
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
        
        # Determine related object and URL
        related_object = None
        related_url = None
        related_label = None
        
        # Parse notification type to determine related object
        if 'appointment' in notification.notification_type:
            related_label = 'View Appointment'
            if notification.url:
                related_url = notification.url
            else:
                related_url = '#'
        elif 'prescription' in notification.notification_type:
            related_label = 'View Prescription'
            if notification.url:
                related_url = notification.url
            else:
                related_url = '#'
        elif 'lab' in notification.notification_type:
            related_label = 'View Laboratory Request'
            if notification.url:
                related_url = notification.url
            else:
                related_url = '#'
        elif notification.notification_type == 'lab_report_ready':
            related_label = 'View Lab Report'
            if notification.url:
                related_url = notification.url
            else:
                related_url = '#'
        
        # ✅ Get previous and next notifications (deleted_at সরানো হয়েছে)
        previous = Notification.objects.filter(
            recipient=request.user,
            created_at__gt=notification.created_at,
        ).order_by('created_at').first()
        
        next_notification = Notification.objects.filter(
            recipient=request.user,
            created_at__lt=notification.created_at,
        ).order_by('-created_at').first()
        
        context = {
            'doctor': doctor,
            'notification': notification,
            'related_object': related_object,
            'related_url': related_url,
            'related_label': related_label,
            'previous': previous,
            'next_notification': next_notification,
            'today': timezone.now().date(),
        }
        
        return render(request, self.template_name, context)