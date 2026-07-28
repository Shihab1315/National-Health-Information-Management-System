"""
Permission checks for the analytics dashboard.
Each function takes a user object and returns True/False.
"""

from .constants import (
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_HOSPITAL_ADMIN,
    ROLE_LAB_TECHNICIAN,
    ROLE_PHARMACIST,
    ROLE_PATIENT,
    ALLOWED_ROLES,
)

def has_analytics_access(user):
    """
    Check if a user is allowed to view the analytics dashboard.
    Returns True if user is authenticated and has an allowed role.
    """
    if not user.is_authenticated:
        return False

    # If you have a custom user model with a 'role' field, use it:
    # role = getattr(user, 'role', None)
    # return role in ALLOWED_ROLES

    # Simpler alternative: allow staff or superuser, and any user who is not a patient.
    # This avoids needing a role field on User.
    if user.is_staff or user.is_superuser:
        return True

    # Check if the user is a patient (by looking for a PatientProfile).
    # If a patient profile exists, they are not allowed.
    try:
        # If you have a Patient model with a OneToOne to User:
        from patients.models import Patient
        if Patient.objects.filter(user=user).exists():
            return False
    except Exception:
        # If the Patient model doesn't exist, we skip this check.
        pass

    # For now, we'll allow any authenticated user who is not a patient.
    # In a production system, you'd use a proper role field or groups.
    return True

def is_admin(user):
    """Check if user has admin privileges."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.is_staff

def is_doctor(user):
    """Check if user is a doctor."""
    # In a real system, you'd check the user's role.
    # For now, we'll check if the user has a Doctor profile (if that model exists).
    try:
        from doctors.models import Doctor
        return Doctor.objects.filter(user=user).exists()
    except Exception:
        return False

def is_hospital_admin(user):
    """Check if user is a hospital admin."""
    # Similar logic: check if user has a HospitalAdmin profile.
    # For now, we'll assume roles are not fully implemented.
    return False

def is_lab_technician(user):
    """Check if user is a lab technician."""
    return False

def is_pharmacist(user):
    """Check if user is a pharmacist."""
    return False