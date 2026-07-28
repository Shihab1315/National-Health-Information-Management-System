# prescriptions/admin.py
"""
Django Admin configuration for the Prescription module.

Provides a professional interface with custom list displays, filters,
search, inline medicines, actions, and performance optimizations.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages

from .models import Prescription, PrescriptionMedicine


# ---------- Inline for Medicines ----------
class PrescriptionMedicineInline(admin.TabularInline):
    """Inline editing for prescription medicines."""
    model = PrescriptionMedicine
    extra = 1
    min_num = 0
    max_num = 20
    fields = (
        'medicine_name', 'dosage', 'frequency', 'duration', 'route',
        'instruction', 'before_food', 'after_food', 'morning', 'afternoon', 'night', 'notes'
    )
    classes = ['collapse']
    verbose_name = _('Medicine')
    verbose_name_plural = _('Medicines')


# ---------- Custom Admin Actions ----------
@admin.action(description=_("Mark selected prescriptions as issued"))
def mark_issued(modeladmin, request, queryset):
    """Bulk issue prescriptions (change status from Draft to Issued)."""
    eligible = queryset.filter(status=Prescription.Status.DRAFT)
    updated = eligible.update(status=Prescription.Status.ISSUED)
    modeladmin.message_user(
        request,
        _("%(count)s prescription(s) marked as issued.") % {'count': updated},
        messages.SUCCESS
    )


@admin.action(description=_("Mark selected prescriptions as completed"))
def mark_completed(modeladmin, request, queryset):
    """Bulk complete prescriptions (only Issued ones)."""
    eligible = queryset.filter(status=Prescription.Status.ISSUED)
    updated = eligible.update(status=Prescription.Status.COMPLETED)
    modeladmin.message_user(
        request,
        _("%(count)s prescription(s) marked as completed.") % {'count': updated},
        messages.SUCCESS
    )


@admin.action(description=_("Mark selected prescriptions as cancelled"))
def mark_cancelled(modeladmin, request, queryset):
    """Bulk cancel prescriptions (excluding Completed)."""
    eligible = queryset.exclude(status=Prescription.Status.COMPLETED)
    updated = eligible.update(status=Prescription.Status.CANCELLED)
    modeladmin.message_user(
        request,
        _("%(count)s prescription(s) cancelled.") % {'count': updated},
        messages.WARNING
    )


@admin.action(description=_("Soft delete selected prescriptions"))
def soft_delete_selected(modeladmin, request, queryset):
    """Soft delete prescriptions (set deleted_at)."""
    updated = queryset.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
    modeladmin.message_user(
        request,
        _("%(count)s prescription(s) soft deleted.") % {'count': updated},
        messages.WARNING
    )


@admin.action(description=_("Restore selected prescriptions"))
def restore_selected(modeladmin, request, queryset):
    """Restore soft-deleted prescriptions."""
    updated = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
    modeladmin.message_user(
        request,
        _("%(count)s prescription(s) restored.") % {'count': updated},
        messages.SUCCESS
    )


# ---------- Admin Class ----------
@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Admin interface for Prescription model with advanced features."""

    # ----- List View Configuration -----
    list_display = (
        'prescription_number',
        'appointment',
        'patient',
        'doctor',
        'hospital',
        'status',
        'created_at',
    )
    list_filter = (
        'status',
        'hospital',
        'doctor',
        'created_at',
        'deleted_at',
    )
    search_fields = (
        'prescription_number',
        'appointment__appointment_number',
        'patient__user__first_name',
        'patient__user__last_name',
        'doctor__user__first_name',
        'doctor__user__last_name',
        'diagnosis',
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    # ----- Inlines -----
    inlines = [PrescriptionMedicineInline]

    # ----- Form / Detail View -----
    autocomplete_fields = ('appointment', 'doctor', 'patient', 'hospital')

    readonly_fields = (
        'prescription_number',
        'appointment',
        'hospital',
        'doctor',
        'patient',
        'created_at',
        'updated_at',
        'deleted_at',
        'created_by',
        'updated_by',
        'doctor_signature',
        'qr_code',
    )

    fieldsets = (
        (None, {
            'fields': (
                'prescription_number',
                'appointment',
                'hospital',
                'doctor',
                'patient',
                'status',
            )
        }),
        (_('Clinical Information'), {
            'fields': (
                'diagnosis',
                'symptoms',
                'clinical_notes',
                'advice',
            )
        }),
        (_('Follow-up & Additional'), {
            'fields': (
                'follow_up_date',
                'doctor_signature',
                'qr_code',
            )
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at',
                'updated_at',
                'deleted_at',
            ),
            'classes': ('collapse',),
        }),
        (_('Audit Trail'), {
            'fields': (
                'created_by',
                'updated_by',
            ),
            'classes': ('collapse',),
        }),
    )

    # ----- Actions -----
    actions = [
        mark_issued,
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
            'appointment',
            'hospital',
            'doctor',
            'patient',
            'doctor__user',
            'patient__user',
            'created_by',
            'updated_by',
        ).prefetch_related('medicines')

    # ----- Save & Audit -----
    def save_model(self, request, obj, form, change):
        """Set created_by on creation, updated_by on update."""
        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    # ----- Custom label for appointment in autocomplete -----
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'appointment':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                deleted_at__isnull=True
            ).select_related('patient', 'doctor')
        elif db_field.name == 'doctor':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                is_active=True
            ).select_related('user')
        elif db_field.name == 'patient':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                is_active=True
            ).select_related('user')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ---------- Register Medicine model (optional, if you want a separate admin) ----------
@admin.register(PrescriptionMedicine)
class PrescriptionMedicineAdmin(admin.ModelAdmin):
    """Admin interface for PrescriptionMedicine (optional standalone view)."""
    list_display = ('prescription', 'medicine_name', 'dosage', 'frequency', 'route')
    list_filter = ('frequency', 'route', 'prescription__status')
    search_fields = ('medicine_name', 'prescription__prescription_number')
    readonly_fields = ('prescription',)
    autocomplete_fields = ('prescription',)