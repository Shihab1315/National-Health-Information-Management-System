from .models import User

def is_doctor(user):
    return user.is_authenticated and user.role == User.Role.DOCTOR

def is_patient(user):
    return user.is_authenticated and user.role == User.Role.PATIENT

def is_admin(user):
    return user.is_authenticated and user.role in [User.Role.SUPER_ADMIN, User.Role.HOSPITAL_ADMIN]

def is_hospital_admin(user):
    return user.is_authenticated and user.role == User.Role.HOSPITAL_ADMIN

def is_super_admin(user):
    return user.is_authenticated and user.role == User.Role.SUPER_ADMIN

def is_lab_tech(user):
    return user.is_authenticated and user.role == User.Role.LAB_TECHNICIAN

def is_pharmacist(user):
    return user.is_authenticated and user.role == User.Role.PHARMACIST

def is_receptionist(user):
    return user.is_authenticated and user.role == User.Role.RECEPTIONIST

def can_view_patient_records(user, patient=None):
    """Check if user can view a specific patient's records."""
    if not user.is_authenticated:
        return False
    if user.role in [User.Role.SUPER_ADMIN, User.Role.HOSPITAL_ADMIN, User.Role.DOCTOR, User.Role.RECEPTIONIST]:
        return True
    if user.role == User.Role.PATIENT and patient and user == patient.user:
        return True
    return False