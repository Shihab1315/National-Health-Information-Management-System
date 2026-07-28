from django.contrib import admin
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'health_id',
        'national_id',
        'phone',
        'district',
        'gender',
        'blood_group',
        'is_active',
        'created_at',
    )

    list_filter = (
        'gender',
        'blood_group',
        'district',
        'is_active',
        'created_at',
    )

    search_fields = (
        'full_name',
        'health_id',
        'national_id',
        'phone',
        'email',
    )

    readonly_fields = (
        'health_id',
        'created_at',
        'updated_at',
    )

    ordering = ('-created_at',)

    # Inline removed – medical records are handled by medical_reports app
    # No inline here

    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = "Activate selected patients"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = "Deactivate selected patients"