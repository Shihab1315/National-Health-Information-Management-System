# appointments/admin.py
"""
Django Admin configuration for the Appointment module.

Provides a professional interface with custom list displays, filters,
search, actions, and performance optimizations.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages

from .models import Appointment


# ---------- Custom Admin Actions ----------

@admin.action(description=_("Mark selected appointments as confirmed"))
def mark_confirmed(modeladmin, request, queryset):
    """Bulk confirm pending appointments."""
    updated = queryset.filter(status='pending').update(
        status='confirmed',
        confirmed_at=timezone.now()
    )
    modeladmin.message_user(
        request,
        _("%(count)s appointment(s) marked as confirmed.") % {'count': updated},
        messages.SUCCESS
    )


@admin.action(description=_("Mark selected appointments as completed"))
def mark_completed(modeladmin, request, queryset):
    """Bulk complete appointments (excluding cancelled/completed)."""
    updated = queryset.exclude(status__in=['cancelled', 'completed']).update(
        status='completed',
        completed_at=timezone.now()
    )
    modeladmin.message_user(
        request,
        _("%(count)s appointment(s) marked as completed.") % {'count': updated},
        messages.SUCCESS
    )


@admin.action(description=_("Mark selected appointments as cancelled"))
def mark_cancelled(modeladmin, request, queryset):
    """Bulk cancel appointments (excluding completed)."""
    updated = queryset.exclude(status='completed').update(
        status='cancelled',
        cancelled_at=timezone.now()
    )
    modeladmin.message_user(
        request,
        _("%(count)s appointment(s) cancelled.") % {'count': updated},
        messages.WARNING
    )


@admin.action(description=_("Soft delete selected appointments"))
def soft_delete_selected(modeladmin, request, queryset):
    """Mark selected appointments as deleted (soft delete)."""
    updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
    modeladmin.message_user(
        request,
        _("%(count)s appointment(s) soft deleted.") % {'count': updated},
        messages.WARNING
    )


@admin.action(description=_("Restore selected appointments"))
def restore_selected(modeladmin, request, queryset):
    """Restore soft‑deleted appointments."""
    updated = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
    modeladmin.message_user(
        request,
        _("%(count)s appointment(s) restored.") % {'count': updated},
        messages.SUCCESS
    )


# ---------- Admin Class ----------

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Appointment model with advanced features.
    """

    # ----- List View Configuration -----
    list_display = (
        'appointment_number',
        'patient',
        'doctor',
        'hospital',
        'appointment_date',
        'appointment_time',
        'status',
        'token',
        'created_at',
    )
    list_filter = (
        'status',
        'appointment_date',
        'hospital',
        'doctor',
        'created_at',
    )
    search_fields = (
        'appointment_number',
        'token',
        'patient__user__first_name',
        'patient__user__last_name',
        'patient__user__email',
        'doctor__user__first_name',
        'doctor__user__last_name',
        'hospital__name',
        'reason',
    )
    ordering = ('-appointment_date', '-appointment_time')
    date_hierarchy = 'appointment_date'

    # ----- Form / Detail View -----
    autocomplete_fields = ('hospital', 'doctor', 'patient')

    readonly_fields = (
        'appointment_number',
        'token',
        'created_at',
        'updated_at',
        'deleted_at',
        'created_by',
        'confirmed_at',
        'confirmed_by',
        'cancelled_at',
        'cancelled_by',
        'completed_at',
        'completed_by',
        'rescheduled_at',
        'rescheduled_by',
    )

    fieldsets = (
        (None, {
            'fields': (
                'appointment_number',
                'token',
                'hospital',
                'doctor',
                'patient',
            )
        }),
        (_('Date & Time'), {
            'fields': ('appointment_date', 'appointment_time')
        }),
        (_('Status'), {
            'fields': ('status', 'reason')
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at',
                'updated_at',
                'deleted_at',
                'confirmed_at',
                'cancelled_at',
                'completed_at',
                'rescheduled_at',
            ),
            'classes': ('collapse',),
        }),
        (_('Audit Trail'), {
            'fields': (
                'created_by',
                'confirmed_by',
                'cancelled_by',
                'completed_by',
                'rescheduled_by',
            ),
            'classes': ('collapse',),
        }),
    )

    # ----- Actions -----
    actions = [
        mark_confirmed,
        mark_completed,
        mark_cancelled,
        soft_delete_selected,
        restore_selected,
    ]

    # ----- Performance Optimisation -----
    def get_queryset(self, request):
        """
        Optimise the admin list view with select_related to reduce queries.
        """
        qs = super().get_queryset(request)
        return qs.select_related(
            'hospital',
            'doctor',
            'patient',
            'doctor__user',
            'patient__user',
            'created_by',
        )

    # ----- Better Foreign Key Dropdowns -----
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Order and filter foreign key choices for a cleaner UI.
        """
        if db_field.name == 'hospital':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                deleted_at__isnull=True
            ).order_by('name')
        elif db_field.name == 'doctor':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                deleted_at__isnull=True
            ).select_related('user').order_by('user__first_name', 'user__last_name')
        elif db_field.name == 'patient':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                deleted_at__isnull=True
            ).select_related('user').order_by('user__first_name', 'user__last_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ----- Auto-set created_by -----
    def save_model(self, request, obj, form, change):
        """Set created_by on creation."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)