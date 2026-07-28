# prescriptions/services.py
"""
Business logic layer for the Prescription module.

All prescription-related operations should be performed through this service
to keep views thin and maintain separation of concerns.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from django.db import transaction
from django.db.models import Q, Count, Sum, F, Value, CharField, QuerySet
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Prescription, PrescriptionMedicine
from appointments.models import Appointment
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()


def create_prescription(
    appointment_id: int,
    diagnosis: str,
    symptoms: str = "",
    clinical_notes: str = "",
    advice: str = "",
    follow_up_date: Optional[date] = None,
    status: str = Prescription.Status.DRAFT,
    created_by=None,
    medicines: Optional[List[Dict]] = None,
) -> Prescription:
    """
    Create a new prescription for a completed appointment.

    Args:
        appointment_id: ID of the appointment.
        diagnosis: Medical diagnosis.
        symptoms: Symptoms (optional).
        clinical_notes: Clinical notes (optional).
        advice: Advice (optional).
        follow_up_date: Follow‑up date (optional).
        status: Prescription status (default: Draft).
        created_by: User creating the prescription.
        medicines: List of dicts with medicine data:
            [
                {
                    'medicine_name': str,
                    'dosage': str,
                    'frequency': str,
                    'duration': str,
                    'route': str,
                    'instruction': str,
                    'before_food': bool,
                    'after_food': bool,
                    'morning': bool,
                    'afternoon': bool,
                    'night': bool,
                    'notes': str,
                },
            ]

    Returns:
        Prescription: The created prescription instance.

    Raises:
        ValidationError: If validation fails (appointment not completed, already has prescription, etc.).
    """
    # Fetch and validate appointment
    try:
        appointment = Appointment.objects.select_related('hospital', 'doctor', 'patient').get(
            pk=appointment_id,
            deleted_at__isnull=True,
            status=Appointment.Status.COMPLETED
        )
    except Appointment.DoesNotExist:
        raise ValidationError(_("Appointment not found or not completed."))

    # Check for existing prescription
    if hasattr(appointment, 'prescription'):
        raise ValidationError(_("This appointment already has a prescription."))

    # Validate follow-up date (if provided)
    if follow_up_date and follow_up_date < timezone.now().date():
        raise ValidationError(_("Follow‑up date cannot be in the past."))

    with transaction.atomic():
        # Create prescription
        prescription = Prescription(
            appointment=appointment,
            hospital=appointment.hospital,
            doctor=appointment.doctor,
            patient=appointment.patient,
            diagnosis=diagnosis,
            symptoms=symptoms,
            clinical_notes=clinical_notes,
            advice=advice,
            follow_up_date=follow_up_date,
            status=status,
            created_by=created_by,
            # Prescription number will be auto‑generated in the model's save()
        )
        prescription.full_clean()
        prescription.save()

        # Create medicine items if provided
        if medicines:
            for med_data in medicines:
                PrescriptionMedicine.objects.create(
                    prescription=prescription,
                    **med_data
                )

        return prescription


def update_prescription(
    prescription_id: int,
    diagnosis: str = None,
    symptoms: str = None,
    clinical_notes: str = None,
    advice: str = None,
    follow_up_date: Optional[date] = None,
    status: str = None,
    updated_by=None,
    medicines: Optional[List[Dict]] = None,
) -> Prescription:
    """
    Update an existing prescription and optionally replace its medicines.

    Args:
        prescription_id: ID of the prescription.
        Other fields: same as create_prescription.
        medicines: If provided, replace all existing medicine items with new ones.

    Returns:
        Prescription: The updated instance.

    Raises:
        ValidationError: If invalid data or prescription not found.
    """
    prescription = get_prescription_or_404(prescription_id)

    # Prevent updates if cancelled
    if prescription.is_cancelled():
        raise ValidationError(_("Cannot update a cancelled prescription."))

    # Update fields if provided
    if diagnosis is not None:
        prescription.diagnosis = diagnosis
    if symptoms is not None:
        prescription.symptoms = symptoms
    if clinical_notes is not None:
        prescription.clinical_notes = clinical_notes
    if advice is not None:
        prescription.advice = advice
    if follow_up_date is not None:
        if follow_up_date < timezone.now().date():
            raise ValidationError(_("Follow‑up date cannot be in the past."))
        prescription.follow_up_date = follow_up_date
    if status is not None:
        # Validate status transition
        if prescription.status == Prescription.Status.CANCELLED:
            raise ValidationError(_("Cannot change status of a cancelled prescription."))
        if status == Prescription.Status.COMPLETED and prescription.status == Prescription.Status.DRAFT:
            raise ValidationError(_("Cannot mark a draft prescription as completed. Please issue it first."))
        prescription.status = status

    prescription.updated_by = updated_by
    prescription.full_clean()

    with transaction.atomic():
        prescription.save()

        # Replace medicines if provided
        if medicines is not None:
            # Delete existing medicines
            prescription.medicines.all().delete()
            # Create new ones
            for med_data in medicines:
                PrescriptionMedicine.objects.create(
                    prescription=prescription,
                    **med_data
                )

    return prescription


def issue_prescription(prescription_id: int, issued_by=None) -> Prescription:
    """
    Issue a prescription (change status from Draft to Issued).

    Args:
        prescription_id: ID of the prescription.
        issued_by: User issuing the prescription.

    Returns:
        Prescription: The updated instance.

    Raises:
        ValidationError: If not in draft status or already issued.
    """
    prescription = get_prescription_or_404(prescription_id)

    if prescription.status != Prescription.Status.DRAFT:
        raise ValidationError(_("Only draft prescriptions can be issued."))

    if not prescription.diagnosis:
        raise ValidationError(_("Cannot issue a prescription without diagnosis."))

    with transaction.atomic():
        prescription.status = Prescription.Status.ISSUED
        prescription.updated_by = issued_by
        prescription.full_clean()
        prescription.save()
        # Signal will send notification via post_save
        return prescription


def complete_prescription(prescription_id: int, completed_by=None) -> Prescription:
    """
    Mark a prescription as completed (after it has been fulfilled or finalised).

    Args:
        prescription_id: ID of the prescription.
        completed_by: User marking complete.

    Returns:
        Prescription: The updated instance.

    Raises:
        ValidationError: If not in issued status or already completed/cancelled.
    """
    prescription = get_prescription_or_404(prescription_id)

    if prescription.status == Prescription.Status.CANCELLED:
        raise ValidationError(_("Cannot complete a cancelled prescription."))
    if prescription.status == Prescription.Status.COMPLETED:
        raise ValidationError(_("Prescription is already completed."))
    if prescription.status != Prescription.Status.ISSUED:
        raise ValidationError(_("Only issued prescriptions can be marked as completed."))

    with transaction.atomic():
        prescription.status = Prescription.Status.COMPLETED
        prescription.updated_by = completed_by
        prescription.full_clean()
        prescription.save()
        # Signal: will update appointment has_prescription? Already true.
        return prescription


def cancel_prescription(prescription_id: int, cancelled_by=None) -> Prescription:
    """
    Cancel a prescription.

    Args:
        prescription_id: ID of the prescription.
        cancelled_by: User cancelling.

    Returns:
        Prescription: The updated instance.

    Raises:
        ValidationError: If already completed or cancelled.
    """
    prescription = get_prescription_or_404(prescription_id)

    if prescription.status == Prescription.Status.COMPLETED:
        raise ValidationError(_("Cannot cancel a completed prescription."))
    if prescription.status == Prescription.Status.CANCELLED:
        raise ValidationError(_("Prescription is already cancelled."))

    with transaction.atomic():
        prescription.status = Prescription.Status.CANCELLED
        prescription.updated_by = cancelled_by
        prescription.full_clean()
        prescription.save()
        return prescription


def soft_delete_prescription(prescription_id: int, deleted_by=None) -> None:
    """
    Soft‑delete a prescription (set deleted_at).

    Args:
        prescription_id: ID of the prescription.
        deleted_by: User performing the deletion (optional).
    """
    prescription = get_prescription_or_404(prescription_id)
    if prescription.status == Prescription.Status.ISSUED:
        # Optionally, prevent deletion of issued prescriptions
        raise ValidationError(_("Cannot delete an issued prescription. Please cancel it first."))
    prescription.delete()  # uses soft delete via model's delete()


def generate_qr_code(prescription: Prescription) -> str:
    """
    Generate a QR code string for the prescription.

    In a real implementation, this would use qrcode library to generate an image.
    For now, we return a placeholder string.

    Args:
        prescription: Prescription instance.

    Returns:
        str: QR code data (or placeholder).
    """
    # This is a placeholder. You can integrate with a QR library later.
    data = f"RX:{prescription.prescription_number}:{prescription.appointment.id}:{prescription.patient.id}:{prescription.doctor.id}"
    return data


def dashboard_statistics(
    user=None,
    hospital_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get prescription statistics for dashboard.

    Args:
        user: Logged‑in user (for RBAC filtering).
        hospital_id: Optional hospital filter.
        doctor_id: Optional doctor filter.

    Returns:
        Dict with counts: total, today, issued, draft, completed, cancelled,
        by_doctor, by_hospital.
    """
    qs = Prescription.objects.filter(deleted_at__isnull=True)

    # Apply RBAC filtering (to be implemented based on user role)
    if user:
        qs = filter_prescriptions_by_user(user, qs)

    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)

    total = qs.count()
    today = qs.filter(created_at__date=timezone.now().date()).count()

    issued = qs.filter(status=Prescription.Status.ISSUED).count()
    draft = qs.filter(status=Prescription.Status.DRAFT).count()
    completed = qs.filter(status=Prescription.Status.COMPLETED).count()
    cancelled = qs.filter(status=Prescription.Status.CANCELLED).count()

    # Count per doctor
    by_doctor = qs.values('doctor__user__first_name', 'doctor__user__last_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Count per hospital
    by_hospital = qs.values('hospital__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    return {
        'total': total,
        'today': today,
        'issued': issued,
        'draft': draft,
        'completed': completed,
        'cancelled': cancelled,
        'by_doctor': list(by_doctor),
        'by_hospital': list(by_hospital),
    }


def search_prescriptions(query: str) -> QuerySet:
    """
    Search prescriptions by prescription number, patient name, doctor name, or appointment number.

    Args:
        query: Search string.

    Returns:
        QuerySet of matching prescriptions.
    """
    if not query:
        return Prescription.objects.none()

    q = Q()
    q |= Q(prescription_number__icontains=query)
    q |= Q(patient__user__first_name__icontains=query)
    q |= Q(patient__user__last_name__icontains=query)
    q |= Q(doctor__user__first_name__icontains=query)
    q |= Q(doctor__user__last_name__icontains=query)
    q |= Q(appointment__appointment_number__icontains=query)

    return Prescription.objects.filter(q, deleted_at__isnull=True).select_related(
        'appointment', 'hospital', 'doctor', 'patient',
        'doctor__user', 'patient__user'
    )


def filter_prescriptions(
    status: Optional[str] = None,
    doctor_id: Optional[int] = None,
    hospital_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    is_active: bool = True,
) -> QuerySet:
    """
    Filter prescriptions by various criteria.

    Args:
        status: Prescription status.
        doctor_id: Doctor ID.
        hospital_id: Hospital ID.
        patient_id: Patient ID.
        date_from: Start date (created_at >= date_from).
        date_to: End date (created_at <= date_to).
        is_active: Include only active (not soft‑deleted) records.

    Returns:
        QuerySet of filtered prescriptions.
    """
    qs = Prescription.objects.all()
    if is_active:
        qs = qs.filter(deleted_at__isnull=True)
    else:
        qs = qs.filter(deleted_at__isnull=False)

    if status:
        qs = qs.filter(status=status)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    return qs.select_related('appointment', 'hospital', 'doctor', 'patient', 'doctor__user', 'patient__user')


def get_prescription_or_404(prescription_id: int) -> Prescription:
    """
    Helper to fetch a prescription or raise ValidationError.

    Args:
        prescription_id: ID of the prescription.

    Returns:
        Prescription instance.

    Raises:
        ValidationError: If not found or soft‑deleted.
    """
    try:
        return Prescription.objects.get(pk=prescription_id, deleted_at__isnull=True)
    except Prescription.DoesNotExist:
        raise ValidationError(_("Prescription not found."))


def get_prescription_with_details(prescription_id: int) -> Prescription:
    """
    Fetch a prescription with all related data (for detail view).

    Args:
        prescription_id: ID of the prescription.

    Returns:
        Prescription with related fields loaded.
    """
    return get_prescription_or_404(prescription_id)


def get_prescriptions_by_doctor(doctor_id: int) -> QuerySet:
    """
    Get all prescriptions for a specific doctor.

    Args:
        doctor_id: Doctor ID.

    Returns:
        QuerySet of prescriptions.
    """
    return Prescription.objects.filter(
        doctor_id=doctor_id,
        deleted_at__isnull=True
    ).select_related('appointment', 'patient').order_by('-created_at')


def get_prescriptions_by_patient(patient_id: int) -> QuerySet:
    """
    Get all prescriptions for a specific patient.

    Args:
        patient_id: Patient ID.

    Returns:
        QuerySet of prescriptions.
    """
    return Prescription.objects.filter(
        patient_id=patient_id,
        deleted_at__isnull=True
    ).select_related('appointment', 'doctor').order_by('-created_at')


def filter_prescriptions_by_user(user, queryset):
    """
    Apply RBAC filtering: restrict queryset based on user's role.

    Args:
        user: User instance.
        queryset: Base queryset.

    Returns:
        Filtered queryset.
    """
    if not user or not user.is_authenticated:
        return queryset.none()

    if user.role == 'super_admin':
        return queryset  # full access
    elif user.role == 'hospital_admin':
        # If hospital_admin has a linked hospital (via profile), filter by that hospital.
        # For now, assume we have a hospital field in user profile or we filter through hospital admin relation.
        # We'll skip for simplicity, but we can implement if needed.
        # Here we assume hospital_admin can view prescriptions for their hospital.
        try:
            hospital = user.hospital  # if user has a hospital field
        except AttributeError:
            # fallback: allow all? or restrict to none
            return queryset.none()
        return queryset.filter(hospital=hospital)
    elif user.role == 'doctor':
        # Filter by doctor linked to this user
        try:
            doctor = Doctor.objects.get(user=user)
            return queryset.filter(doctor=doctor)
        except Doctor.DoesNotExist:
            return queryset.none()
    elif user.role == 'receptionist':
        # Receptionist might have access to all or by hospital
        # For now, allow all (or filter by hospital if needed)
        return queryset
    elif user.role == 'patient':
        # Patient sees only their own prescriptions
        try:
            patient = Patient.objects.get(user=user)
            return queryset.filter(patient=patient)
        except Patient.DoesNotExist:
            return queryset.none()
    else:
        return queryset.none()