# laboratory/admin.py
"""
Django Admin configuration for the Laboratory module.
Registers all five models with custom admin classes, inlines, and optimizations.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import TestCategory, LaboratoryTest, LabOrder, LabOrderItem, LabResult


class LabOrderItemInline(admin.TabularInline):
    """Inline editing for lab order items."""
    model = LabOrderItem
    extra = 1
    min_num = 0
    max_num = 20
    fields = ('test', 'notes')
    autocomplete_fields = ('test',)
    classes = ['collapse']
    verbose_name = _('Test Item')
    verbose_name_plural = _('Test Items')


class LabResultInline(admin.StackedInline):
    """Inline for lab result (OneToOne with LabOrderItem)."""
    model = LabResult
    extra = 0
    max_num = 1
    fields = ('result', 'interpretation', 'remarks', 'report_file', 'technician', 'verified_by', 'verified_at')
    readonly_fields = ('technician', 'verified_by', 'verified_at')
    classes = ['collapse']
    verbose_name = _('Result')
    verbose_name_plural = _('Result')


@admin.register(TestCategory)
class TestCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


@admin.register(LaboratoryTest)
class LaboratoryTestAdmin(admin.ModelAdmin):
    list_display = ('test_code', 'name', 'category', 'is_active', 'price')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('test_code', 'name', 'description')
    ordering = ('name',)
    autocomplete_fields = ('category',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'prescription', 'patient', 'doctor', 'hospital',
        'status', 'ordered_date', 'is_active_display'   # now this method exists
    )
    list_filter = ('status', 'hospital', 'doctor', 'ordered_date', 'deleted_at')
    search_fields = (
        'order_number',
        'prescription__prescription_number',
        'patient__user__first_name',
        'patient__user__last_name',
        'doctor__user__first_name',
        'doctor__user__last_name',
        'notes'
    )
    ordering = ('-ordered_date',)
    date_hierarchy = 'ordered_date'
    autocomplete_fields = ('prescription',)
    inlines = [LabOrderItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('order_number', 'prescription')
        }),
        (_('Status & Notes'), {
            'fields': ('status', 'notes')
        }),
        (_('Audit'), {
            'fields': ('ordered_date', 'created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = (
        'order_number',
        'ordered_date',
        'created_at',
        'updated_at',
        'deleted_at',
        'created_by',
        'updated_by',
    )

    # ----- ADD THE MISSING METHODS -----
    def get_queryset(self, request):
        """Optimize admin list view with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related(
            'prescription', 'appointment', 'patient', 'doctor', 'hospital',
            'patient__user', 'doctor__user'
        ).prefetch_related('items', 'items__test')

    def is_active_display(self, obj):
        """Display whether the order is soft‑deleted."""
        return obj.deleted_at is None
    is_active_display.boolean = True
    is_active_display.short_description = _('Active')

    def save_model(self, request, obj, form, change):
        """Set created_by / updated_by automatically."""
        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LabOrderItem)
class LabOrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'lab_order', 'test', 'has_result')
    list_filter = ('lab_order__status', 'test__category')
    search_fields = ('lab_order__order_number', 'test__name')
    autocomplete_fields = ('lab_order', 'test')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    def has_result(self, obj):
        return hasattr(obj, 'result')
    has_result.boolean = True
    has_result.short_description = _('Has Result')


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('order_item', 'result_preview', 'technician', 'verified_by', 'verified_at')
    list_filter = ('verified_by', 'created_at')
    search_fields = ('order_item__lab_order__order_number', 'result', 'remarks')
    
    # Make order_item editable and searchable via autocomplete
    autocomplete_fields = ('order_item',)
    
    # Technician and verified_by are manually set, but we allow selecting them in admin
    # Only make audit fields read-only
    readonly_fields = (
        'technician',
        'verified_by',
        'verified_at',
        'created_at',
        'updated_at',
        'deleted_at',
    )
    
    # Optionally, set technician to current user on save (not necessary but nice)
    def save_model(self, request, obj, form, change):
        if not change and not obj.technician:
            obj.technician = request.user
        super().save_model(request, obj, form, change)

    def result_preview(self, obj):
        return obj.result[:50] + '...' if len(obj.result) > 50 else obj.result
    result_preview.short_description = _('Result')