from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'hospital', 'is_staff', 'is_active')
    list_filter = ('role', 'hospital', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('NHIMS Fields', {'fields': ('role', 'phone_number', 'nid', 'profile_picture', 'hospital')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('NHIMS Fields', {'fields': ('role', 'phone_number', 'nid', 'profile_picture', 'hospital')}),
    )
    search_fields = ('username', 'email', 'phone_number', 'nid')