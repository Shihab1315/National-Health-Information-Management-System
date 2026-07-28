from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy

class RoleRequiredMixin(AccessMixin):
    """CBV mixin to require specific roles."""
    allowed_roles = []
    redirect_url = '/'  # ডিফল্ট রিডিরেক্ট URL

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Check if user has any of the allowed roles
        if not request.user.has_role(self.allowed_roles):
            messages.error(request, "You do not have permission to access this page.")
            return redirect(self.redirect_url)
        return super().dispatch(request, *args, **kwargs)

# Shortcut mixins
class SuperAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['super_admin']

class HospitalAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['super_admin', 'hospital_admin']

class DoctorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor']

class LabTechnicianRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['super_admin', 'hospital_admin', 'lab_technician']

class PharmacistRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['super_admin', 'hospital_admin', 'pharmacist']

class ReceptionistRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['super_admin', 'hospital_admin', 'receptionist']

class StaffRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'lab_technician', 'pharmacist']