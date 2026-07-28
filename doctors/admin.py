from django.contrib import admin
from .models import Specialty, Doctor

class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)

admin.site.register(Specialty, SpecialtyAdmin)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'doctor_id', 'registration_number',
        'hospital', 'specialty_list', 'experience',
        'is_active', 'is_verified'
    )
    list_filter = ('is_active', 'is_verified', 'gender', 'specialties', 'hospital')
    search_fields = (
        'full_name', 'doctor_id', 'registration_number',
        'national_id', 'phone', 'email'
    )
    readonly_fields = ('doctor_id', 'created_at', 'updated_at')
    filter_horizontal = ('specialties',)

    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'full_name', 'national_id', 'registration_number',
                       'gender', 'date_of_birth', 'phone', 'email')
        }),
        ('Address', {
            'fields': ('address', 'city', 'district', 'zip_code')
        }),
        ('Professional', {
            'fields': ('specialties', 'hospital', 'qualification',
                       'experience', 'consultation_fee')
        }),
        ('Schedule', {
            'fields': ('available_days', 'available_time_start', 'available_time_end')
        }),
        ('Profile', {
            'fields': ('profile_photo', 'bio', 'is_active', 'is_verified')
        }),
        ('System', {
            'fields': ('doctor_id', 'created_at', 'updated_at')
        }),
    )

    actions = ['make_verified', 'make_unverified']

    def make_verified(self, request, queryset):
        queryset.update(is_verified=True)
    make_verified.short_description = "Verify selected doctors"

    def make_unverified(self, request, queryset):
        queryset.update(is_verified=False)
    make_unverified.short_description = "Unverify selected doctors"

    def specialty_list(self, obj):
        return ", ".join([s.name for s in obj.specialties.all()])
    specialty_list.short_description = 'Specialties'