from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Hospital, HospitalDepartment, HospitalFacility,
    HospitalGallery, HospitalReview, HospitalOperatingHour
)


class HospitalDepartmentInline(admin.TabularInline):
    model = HospitalDepartment
    extra = 1
    fields = ('name', 'description', 'head_doctor', 'floor_number', 'phone', 'email', 'active')


class HospitalFacilityInline(admin.TabularInline):
    model = HospitalFacility
    extra = 1
    fields = ('title', 'icon', 'description', 'available', 'display_order')


class HospitalGalleryInline(admin.TabularInline):
    model = HospitalGallery
    extra = 1
    fields = ('image', 'caption', 'display_order')


class HospitalOperatingHourInline(admin.TabularInline):
    model = HospitalOperatingHour
    extra = 1
    fields = ('day', 'open_time', 'close_time', 'is_emergency')


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'hospital_code', 'hospital_type', 'district',
        'total_beds', 'average_rating', 'verified', 'featured', 'active'
    )
    list_filter = (
        'hospital_type', 'ownership', 'district', 'division',
        'verified', 'featured', 'active', 'emergency_available'
    )
    search_fields = (
        'name', 'hospital_code', 'registration_number',
        'license_number', 'email', 'phone'
    )
    readonly_fields = ('hospital_code', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [
        HospitalDepartmentInline,
        HospitalFacilityInline,
        HospitalGalleryInline,
        HospitalOperatingHourInline
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'slug', 'hospital_code', 'registration_number',
                'license_number', 'tin', 'bin', 'hospital_type', 'ownership',
                'established_year'
            )
        }),
        ('Description', {
            'fields': ('description', 'short_description', 'mission', 'vision', 'history')
        }),
        ('Logo & Images', {
            'fields': ('logo', 'cover_image')
        }),
        ('Address & Location', {
            'fields': (
                'country', 'division', 'district', 'upazila', 'city',
                'area', 'postal_code', 'full_address',
                'latitude', 'longitude', 'google_map_link'
            )
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'emergency_phone', 'ambulance_phone', 'website')
        }),
        ('Social Media', {
            'fields': ('facebook', 'linkedin', 'twitter', 'instagram', 'youtube')
        }),
        ('Facilities (Checkboxes)', {
            'fields': (
                'emergency_available', 'icu', 'nicu', 'ccu', 'emergency_department',
                'operation_theater', 'laboratory', 'radiology', 'mri', 'ct_scan',
                'x_ray', 'ultrasound', 'blood_bank', 'pharmacy', 'vaccination_center',
                'dialysis', 'cancer_unit', 'burn_unit', 'heart_center', 'eye_center',
                'dental_unit'
            )
        }),
        ('Amenities', {
            'fields': (
                'parking', 'wheelchair_access', 'prayer_room', 'cafeteria',
                'atm', 'wifi', 'generator_backup', 'oxygen_plant', 'open_24_hours'
            )
        }),
        ('Statistics', {
            'fields': (
                'total_doctors', 'total_nurses', 'total_beds',
                'available_beds', 'icu_beds', 'emergency_beds'
            )
        }),
        ('Rating', {
            'fields': ('average_rating', 'total_reviews')
        }),
        ('Status', {
            'fields': ('verified', 'featured', 'active', 'is_deleted')
        }),
        ('System', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    actions = ['mark_verified', 'mark_featured', 'activate', 'deactivate']

    def mark_verified(self, request, queryset):
        queryset.update(verified=True)
    mark_verified.short_description = "Mark selected as Verified"

    def mark_featured(self, request, queryset):
        queryset.update(featured=True)
    mark_featured.short_description = "Mark selected as Featured"

    def activate(self, request, queryset):
        queryset.update(active=True)
    activate.short_description = "Activate selected"

    def deactivate(self, request, queryset):
        queryset.update(active=False)
    deactivate.short_description = "Deactivate selected"


@admin.register(HospitalDepartment)
class HospitalDepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'hospital', 'head_doctor', 'active')
    list_filter = ('active', 'hospital')
    search_fields = ('name',)


@admin.register(HospitalFacility)
class HospitalFacilityAdmin(admin.ModelAdmin):
    list_display = ('title', 'hospital', 'available')
    list_filter = ('available',)


@admin.register(HospitalGallery)
class HospitalGalleryAdmin(admin.ModelAdmin):
    list_display = ('hospital', 'caption', 'display_order')
    list_filter = ('hospital',)


@admin.register(HospitalReview)
class HospitalReviewAdmin(admin.ModelAdmin):
    list_display = ('patient', 'hospital', 'rating', 'approved', 'created_at')
    list_filter = ('approved', 'rating', 'hospital')
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)
    approve_reviews.short_description = "Approve selected reviews"


@admin.register(HospitalOperatingHour)
class HospitalOperatingHourAdmin(admin.ModelAdmin):
    list_display = ('hospital', 'get_day_display', 'open_time', 'close_time', 'is_emergency')
    list_filter = ('hospital', 'is_emergency')