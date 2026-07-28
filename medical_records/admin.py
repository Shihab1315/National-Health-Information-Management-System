# medical_records/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.contrib.auth import get_user_model

from .models import (
    MedicalRecord, Allergy, ChronicDisease, PastHistory,
    Vaccination, Attachment, FollowUp
)

User = get_user_model()


# ---------- INLINES ----------
class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    fields = ('file', 'description', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_by', 'uploaded_at')
    classes = ['collapse']
    verbose_name = _('Attachment')
    verbose_name_plural = _('Attachments')
    show_change_link = True


class FollowUpInline(admin.TabularInline):
    model = FollowUp
    extra = 0
    fields = ('scheduled_date', 'status', 'notes', 'reminder_sent')
    readonly_fields = ('scheduled_date',)
    classes = ['collapse']
    verbose_name = _('Follow‑up')
    verbose_name_plural = _('Follow‑ups')
    show_change_link = True


# ---------- ACTIONS ----------
@admin.action(description="Mark selected as Active")
def mark_active(modeladmin, request, queryset):
    queryset.update(is_deleted=False)


@admin.action(description="Mark selected as Deleted")
def mark_deleted(modeladmin, request, queryset):
    queryset.update(is_deleted=True)


# ---------- MEDICAL RECORD ----------
@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = (
        'patient',
        'doctor_name',
        'hospital_name',
        'visit_date',
        'diagnosis',
        'bmi_display',
        'status',
    )
    list_display_links = ('patient', 'diagnosis')
    list_filter = ('status', 'hospital', 'doctor', 'visit_date', 'is_deleted')
    list_select_related = (
        'patient',
        'doctor',
        'hospital',
        'appointment',
        'prescription',
        'lab_order',
    )
    list_per_page = 25
    date_hierarchy = 'visit_date'
    ordering = ('-visit_date',)
    save_on_top = True

    search_fields = (
        'patient__full_name',
        'patient__user__first_name',
        'patient__user__last_name',
        'doctor__full_name',
        'hospital__name',
        'diagnosis',
        'chief_complaint'
    )

    autocomplete_fields = (
        'patient', 'doctor', 'hospital', 'appointment', 'prescription', 'lab_order'
    )
    readonly_fields = ('created_at', 'updated_at', 'bmi_value')
    fieldsets = (
        (None, {
            'fields': ('patient', 'doctor', 'hospital', 'appointment', 'prescription', 'lab_order')
        }),
        (_('Visit Details'), {
            'fields': ('visit_date', 'status', 'chief_complaint', 'symptoms',
                       'history_of_present_illness', 'diagnosis', 'clinical_findings')
        }),
        (_('Vitals'), {
            'fields': ('blood_pressure_systolic', 'blood_pressure_diastolic',
                       'pulse', 'temperature', 'height', 'weight', 'bmi',
                       'oxygen_saturation', 'respiratory_rate')
        }),
        (_('Treatment & Notes'), {
            'fields': ('treatment_plan', 'doctor_notes', 'follow_up_date')
        }),
        (_('Audit'), {
            'fields': ('created_by', 'created_at', 'updated_at', 'is_deleted'),
            'classes': ('collapse',),
        }),
    )
    inlines = [AttachmentInline, FollowUpInline]
    actions = (mark_active, mark_deleted)

    @admin.display(description="BMI")
    def bmi_display(self, obj):
        return obj.bmi_value

    @admin.display(description="Hospital")
    def hospital_name(self, obj):
        return obj.hospital.name if obj.hospital else "-"

    @admin.display(description="Doctor")
    def doctor_name(self, obj):
        return obj.doctor.full_name if obj.doctor else "-"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'patient', 'patient__user', 'doctor', 'hospital',
            'appointment', 'prescription', 'lab_order'
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ---------- ALLERGY ----------
@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'allergen', 'severity', 'recorded_at')
    list_display_links = ('patient',)
    list_filter = ('severity',)
    list_select_related = ('patient',)
    list_per_page = 25
    ordering = ('-recorded_at',)
    search_fields = ('patient__full_name', 'allergen', 'reaction')
    autocomplete_fields = ('patient',)
    readonly_fields = ('recorded_at',)
    actions = (mark_active, mark_deleted)


# ---------- CHRONIC DISEASE ----------
@admin.register(ChronicDisease)
class ChronicDiseaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'disease', 'diagnosed_date', 'is_active')
    list_display_links = ('patient',)
    list_filter = ('disease', 'is_active', 'diagnosed_date')
    list_select_related = ('patient',)
    list_per_page = 25
    ordering = ('-diagnosed_date',)
    search_fields = ('patient__full_name', 'disease', 'notes')
    autocomplete_fields = ('patient',)
    actions = (mark_active, mark_deleted)


# ---------- PAST HISTORY ----------
@admin.register(PastHistory)
class PastHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'recorded_at')
    list_display_links = ('patient',)
    list_filter = ('recorded_at',)
    list_select_related = ('patient',)
    list_per_page = 25
    ordering = ('-recorded_at',)
    search_fields = ('patient__full_name', 'surgeries', 'hospital_admissions', 'family_history')
    autocomplete_fields = ('patient',)
    readonly_fields = ('recorded_at',)
    actions = (mark_active, mark_deleted)


# ---------- VACCINATION ----------
@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'vaccine', 'dose_number', 'administration_date', 'next_due_date')
    list_display_links = ('patient',)
    list_filter = ('vaccine', 'administration_date')
    list_select_related = ('patient',)
    list_per_page = 25
    ordering = ('-administration_date',)
    search_fields = ('patient__full_name', 'vaccine', 'administered_by')
    autocomplete_fields = ('patient',)
    actions = (mark_active, mark_deleted)


# ---------- ATTACHMENT ----------
@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'medical_record', 'description', 'uploaded_by', 'uploaded_at', 'download')
    list_display_links = ('medical_record',)
    list_filter = ('uploaded_at',)
    list_select_related = ('medical_record', 'uploaded_by')
    list_per_page = 25
    ordering = ('-uploaded_at',)
    search_fields = ('medical_record__patient__full_name', 'description')
    autocomplete_fields = ('medical_record', 'uploaded_by')
    readonly_fields = ('uploaded_at',)
    actions = (mark_active, mark_deleted)

    @admin.display(description="Download")
    def download(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄</a>', obj.file.url)
        return "-"


# ---------- FOLLOW-UP ----------
@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'scheduled_date', 'colored_status', 'reminder_sent')
    list_display_links = ('medical_record',)
    list_filter = ('status', 'reminder_sent')
    list_select_related = ('medical_record',)
    list_per_page = 25
    ordering = ('scheduled_date',)
    search_fields = ('medical_record__patient__full_name', 'notes')
    autocomplete_fields = ('medical_record',)
    actions = (mark_active, mark_deleted)

    @admin.display(description="Status")
    def colored_status(self, obj):
        colors = {
            "scheduled": "blue",
            "completed": "green",
            "missed": "red",
            "cancelled": "gray",
        }
        return format_html(
            '<b style="color:{}">{}</b>',
            colors.get(obj.status, "black"),
            obj.get_status_display(),
        )