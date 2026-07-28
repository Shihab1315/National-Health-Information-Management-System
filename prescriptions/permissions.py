# prescriptions/permissions.py
"""
Permission helpers for the Prescription module.

These functions check if a user has the appropriate role/permission
to perform actions on prescriptions. Used in views (with @role_required)
and in templates to conditionally show/hide UI elements.
"""

from typing import Optional, Union
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from .models import Prescription
from doctors.models import Doctor
from patients.models import Patient

User = get_user_model()


# ---------- Role-based permission checks ----------

def can_view_prescription_list(user: User) -> bool:
    """
    Check if a user can view the list of prescriptions.
    Allowed roles: Super Admin, Hospital Admin, Doctor, Receptionist, Pharmacist.
    Patients can view only their own via separate permission.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'pharmacist']
    return user.role in allowed_roles


def can_create_prescription(user: User) -> bool:
    """
    Check if a user can create a new prescription.
    Allowed roles: Super Admin, Hospital Admin, Doctor.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor']
    return user.role in allowed_roles


def can_view_prescription(user: User, prescription: Prescription) -> bool:
    """
    Check if a user can view a specific prescription.
    - Super Admin, Hospital Admin, Doctor, Receptionist, Pharmacist: can view any.
    - Patient: can view only their own prescriptions.
    """
    if user.role in ['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'pharmacist']:
        return True
    if user.role == 'patient':
        return prescription.patient.user_id == user.id
    return False


def can_update_prescription(user: User, prescription: Prescription) -> bool:
    """
    Check if a user can update (edit) a prescription.
    Allowed roles: Super Admin, Hospital Admin, Doctor.
    Doctor can only update their own prescriptions.
    """
    if user.role in ['super_admin', 'hospital_admin']:
        return True
    if user.role == 'doctor':
        # Check if the logged-in doctor is the one who owns this prescription
        try:
            doctor = Doctor.objects.get(user=user)
            return prescription.doctor == doctor and prescription.status in ['draft', 'issued']
        except Doctor.DoesNotExist:
            return False
    return False


def can_delete_prescription(user: User, prescription: Prescription) -> bool:
    """
    Check if a user can delete (soft delete) a prescription.
    Allowed roles: Super Admin, Hospital Admin.
    Cannot delete if status is 'issued' or 'completed' (enforced in service).
    """
    allowed_roles = ['super_admin', 'hospital_admin']
    return user.role in allowed_roles


def can_issue_prescription(user: User, prescription: Prescription) -> bool:
    """
    Check if a user can issue a prescription (change status from Draft to Issued).
    Allowed roles: Super Admin, Hospital Admin, Doctor.
    Doctor can only issue their own prescriptions.
    """
    if user.role in ['super_admin', 'hospital_admin']:
        return True
    if user.role == 'doctor':
        try:
            doctor = Doctor.objects.get(user=user)
            return prescription.doctor == doctor and prescription.status == 'draft'
        except Doctor.DoesNotExist:
            return False
    return False


def can_complete_prescription(user: User, prescription: Prescription) -> bool:
    """
    Check if a user can mark a prescription as completed.
    Allowed roles: Super Admin, Hospital Admin, Doctor.
    Doctor can only complete their own prescriptions.
    """
    if user.role in ['super_admin', 'hospital_admin']:
        return True
    if user.role == 'doctor':
        try:
            doctor = Doctor.objects.get(user=user)
            return prescription.doctor == doctor and prescription.status == 'issued'
        except Doctor.DoesNotExist:
            return False
    return False


def can_cancel_prescription(user: User, prescription: Prescription) -> bool:
    """
    Check if a user can cancel a prescription.
    Allowed roles: Super Admin, Hospital Admin, Doctor.
    Doctor can only cancel their own prescriptions.
    """
    if user.role in ['super_admin', 'hospital_admin']:
        return True
    if user.role == 'doctor':
        try:
            doctor = Doctor.objects.get(user=user)
            return prescription.doctor == doctor and prescription.status not in ['completed', 'cancelled']
        except Doctor.DoesNotExist:
            return False
    return False


# ---------- Helper functions for views ----------

def filter_prescriptions_by_user(user: User, queryset):
    """
    Filter a queryset of prescriptions based on user role.
    - Super Admin, Hospital Admin: see all (Hospital Admin may be filtered by hospital later).
    - Doctor: see their own prescriptions.
    - Receptionist: see all (or per hospital if multi-hospital).
    - Pharmacist: see all (or per hospital if multi-hospital).
    - Patient: see only their own.
    """
    if user.role == 'super_admin':
        return queryset
    if user.role == 'hospital_admin':
        # If hospital_admin is linked to a hospital, filter by that hospital
        # For now, we assume they have access to all (or we can filter by hospital if available)
        # You can add hospital filtering if the user profile has a hospital relation.
        # We'll keep it as is.
        return queryset
    if user.role == 'doctor':
        # Filter by doctor profile linked to user
        try:
            doctor = Doctor.objects.get(user=user)
            return queryset.filter(doctor=doctor)
        except Doctor.DoesNotExist:
            return queryset.none()
    if user.role == 'receptionist':
        # Receptionist might see all appointments for their hospital
        # For simplicity, return all
        return queryset
    if user.role == 'pharmacist':
        # Pharmacist may see all prescriptions for their hospital
        # For simplicity, return all
        return queryset
    if user.role == 'patient':
        try:
            patient = Patient.objects.get(user=user)
            return queryset.filter(patient=patient)
        except Patient.DoesNotExist:
            return queryset.none()
    # Default: empty queryset
    return queryset.none()