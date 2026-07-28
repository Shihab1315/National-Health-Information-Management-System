# appointments/permissions.py
"""
Permission helpers for the Appointment module.

These functions check if a user has the appropriate role/permission
to perform actions on appointments. Used in views (with @role_required)
and in templates to conditionally show/hide UI elements.
"""

from typing import Optional, Union, Protocol
from django.core.exceptions import PermissionDenied

from .models import Appointment


class UserProtocol(Protocol):
    """Protocol describing the user attributes used in this module."""
    role: str
    id: int


User = UserProtocol


# ---------- Role-based permission checks ----------

def can_view_appointment_list(user: User) -> bool:
    """
    Check if a user can view the list of appointments.
    Allowed roles: Super Admin, Hospital Admin, Doctor, Receptionist.
    Patients may see only their own via separate permission.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']
    return user.role in allowed_roles


def can_create_appointment(user: User) -> bool:
    """
    Check if a user can create a new appointment.
    Allowed roles: Super Admin, Hospital Admin, Doctor, Receptionist.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']
    return user.role in allowed_roles


def can_view_appointment(user: User, appointment: Appointment) -> bool:
    """
    Check if a user can view a specific appointment.
    - Super Admin, Hospital Admin, Doctor, Receptionist: can view any.
    - Patient: can view only their own appointments.
    """
    if user.role in ['super_admin', 'hospital_admin', 'doctor', 'receptionist']:
        return True
    if user.role == 'patient':
        return appointment.patient.user_id == user.id
    return False


def can_update_appointment(user: User, appointment: Appointment) -> bool:
    """
    Check if a user can update (edit) an appointment.
    Allowed roles: Super Admin, Hospital Admin, Doctor, Receptionist.
    Note: Doctor might update only certain fields, but we allow.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']
    return user.role in allowed_roles


def can_cancel_appointment(user: User, appointment: Appointment) -> bool:
    """
    Check if a user can cancel an appointment.
    Same as update permission.
    """
    return can_update_appointment(user, appointment)


def can_confirm_appointment(user: User, appointment: Appointment) -> bool:
    """
    Check if a user can confirm a pending appointment.
    Allowed roles: Super Admin, Hospital Admin, Receptionist, Doctor.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'receptionist', 'doctor']
    return user.role in allowed_roles


def can_complete_appointment(user: User, appointment: Appointment) -> bool:
    """
    Check if a user can mark an appointment as completed.
    Allowed roles: Super Admin, Hospital Admin, Doctor.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor']
    return user.role in allowed_roles


def can_delete_appointment(user: User, appointment: Appointment) -> bool:
    """
    Check if a user can delete (soft delete) an appointment.
    Only Super Admin and Hospital Admin.
    """
    allowed_roles = ['super_admin', 'hospital_admin']
    return user.role in allowed_roles


# ---------- Helper functions for views ----------

def filter_appointments_by_user(user: User, queryset):
    """
    Filter a queryset of appointments based on user role.
    - Super Admin, Hospital Admin: see all.
    - Doctor: see appointments where they are the doctor.
    - Receptionist: see all (or could be per hospital if multi-hospital).
    - Patient: see only their own.
    """
    if user.role == 'super_admin':
        return queryset
    if user.role == 'hospital_admin':
        # If hospital_admin is linked to a hospital, filter by that hospital
        # Assuming the user has a profile with hospital relation
        # For simplicity, return all (or filter if we have hospital)
        # We'll implement a generic filter if needed.
        return queryset
    if user.role == 'doctor':
        # Filter by doctor profile linked to user
        return queryset.filter(doctor__user_id=user.id)
    if user.role == 'receptionist':
        # Receptionist might see appointments for all hospitals they work for
        # For simplicity, return all
        return queryset
    if user.role == 'patient':
        return queryset.filter(patient__user_id=user.id)
    # Default: empty queryset
    return queryset.none()


def get_allowed_statuses_for_user(user: User) -> list:
    """
    Return a list of appointment statuses that the user is allowed to change to.
    Used in form choice limitations.
    """
    # For simplicity, all statuses for super_admin and hospital_admin
    # For others, restrict
    if user.role in ['super_admin', 'hospital_admin']:
        return ['pending', 'confirmed', 'cancelled', 'completed']
    if user.role == 'doctor':
        return ['confirmed', 'completed']  # Can confirm and complete
    if user.role == 'receptionist':
        return ['pending', 'confirmed', 'cancelled']  # Can confirm and cancel
    # Others (patient) cannot change status
    return []


# ---------- View decorator helper (if needed) ----------
# The existing @role_required decorator is already used.
# We may define a custom permission decorator that uses these functions.

def appointment_permission_required(permission_func):
    """
    Decorator to check a specific appointment permission.
    Example usage:
    @appointment_permission_required(can_update_appointment)
    def update_view(request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        ...
    """
    from functools import wraps
    from django.shortcuts import get_object_or_404

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Assume the view has a 'pk' argument for appointment ID
            pk = kwargs.get('pk')
            if not pk:
                # If no pk, raise error or allow (maybe list view)
                raise PermissionDenied("No appointment ID provided.")
            appointment = get_object_or_404(Appointment, pk=pk, deleted_at__isnull=True)
            if not permission_func(request.user, appointment):
                raise PermissionDenied("You do not have permission for this action.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator