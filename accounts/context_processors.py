from .models import User

def user_role(request):
    """Inject user role and helper functions into every template."""
    if request.user.is_authenticated:
        return {
            'user_role': request.user.role,
            'is_doctor': request.user.is_doctor(),
            'is_patient': request.user.is_patient(),
            'is_hospital_admin': request.user.is_hospital_admin(),
            'is_super_admin': request.user.is_super_admin(),
            'is_lab_technician': request.user.is_lab_technician(),
            'is_pharmacist': request.user.is_pharmacist(),
            'is_receptionist': request.user.is_receptionist(),
            'is_staff': request.user.role in ['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'lab_technician', 'pharmacist']
        }
    return {}