from django.contrib import admin
from .models import LabTechnician

@admin.register(LabTechnician)
class LabTechnicianAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'hospital', 'department', 'is_active', 'created_at']
    list_filter = ['hospital', 'department', 'is_active']
    search_fields = ['full_name', 'user__username', 'phone']
    readonly_fields = ['created_at', 'updated_at']