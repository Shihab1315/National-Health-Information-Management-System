from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.timesince import timesince
from django.urls import reverse

User = get_user_model()


class NotificationManager(models.Manager):
    """Custom manager for Notification model."""

    def unread_count(self, user):
        """Return the number of unread notifications for a user."""
        return self.filter(recipient=user, is_read=False).count()

    def mark_all_as_read(self, user):
        """Mark all notifications for a user as read."""
        return self.filter(recipient=user, is_read=False).update(is_read=True)

    def for_user(self, user, limit=None):
        """Return notifications for a user, ordered newest first."""
        qs = self.filter(recipient=user).order_by('-created_at')
        if limit:
            qs = qs[:limit]
        return qs


class Notification(models.Model):
    """Notification model for system events."""

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    class NotificationType(models.TextChoices):
        APPOINTMENT_BOOKED = 'appointment_booked', 'Appointment Booked'
        APPOINTMENT_CANCELLED = 'appointment_cancelled', 'Appointment Cancelled'
        APPOINTMENT_APPROVED = 'appointment_approved', 'Appointment Approved'
        APPOINTMENT_COMPLETED = 'appointment_completed', 'Appointment Completed'
        PATIENT_REGISTERED = 'patient_registered', 'Patient Registered'
        DOCTOR_ADDED = 'doctor_added', 'Doctor Added'
        HOSPITAL_ADDED = 'hospital_added', 'Hospital Added'
        PRESCRIPTION_GENERATED = 'prescription_generated', 'Prescription Generated'
        LAB_TEST_REQUESTED = 'lab_test_requested', 'Lab Test Requested'
        LAB_REPORT_READY = 'lab_report_ready', 'Lab Report Ready'
        MEDICINE_DISPENSED = 'medicine_dispensed', 'Medicine Dispensed'
        MEDICINE_LOW_STOCK = 'medicine_low_stock', 'Medicine Low Stock'
        REVENUE_ALERT = 'revenue_alert', 'Revenue Alert'
        SYSTEM_NOTIFICATION = 'system_notification', 'System Notification'
        ACCOUNT_NOTIFICATION = 'account_notification', 'Account Notification'

    # Fields
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM_NOTIFICATION
    )
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class, e.g. 'fas fa-bell'")
    color = models.CharField(max_length=20, blank=True, help_text="Tailwind color class, e.g. 'text-blue-400'")
    url = models.CharField(max_length=500, blank=True, help_text="Relative URL to redirect when clicked")
    is_read = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.LOW
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NotificationManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.title} for {self.recipient.username}"

    def mark_as_read(self):
        """Mark this notification as read."""
        self.is_read = True
        self.save(update_fields=['is_read'])

    def get_absolute_url(self):
        """If a URL is not set, fallback to notification center."""
        return self.url or reverse('notifications:center')

    @property
    def time_ago(self):
        """Return human‑readable time difference."""
        from .utils import time_ago as format_time_ago
        return format_time_ago(self.created_at)