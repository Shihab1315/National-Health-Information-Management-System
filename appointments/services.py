# appointments/services.py
"""
Business logic layer for the Appointment module.

All appointment-related operations should be performed through this service
to keep views thin and maintain separation of concerns.
"""

from datetime import date, time, timedelta
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.db.models import Q, QuerySet
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Appointment
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient


def create_appointment(
    hospital_id: int,
    doctor_id: int,
    patient_id: int,
    appointment_date: date,
    appointment_time: time,
    reason: str = "",
    created_by=None,
) -> Appointment:
    """
    Create a new appointment after validating availability and relationships.
    """
    # Fetch and validate related objects using CORRECT field names
    try:
        # Hospital: use is_deleted=False (not deleted_at__isnull)
        hospital = Hospital.objects.get(id=hospital_id, is_deleted=False)
        # Doctor: use is_active=True
        doctor = Doctor.objects.get(id=doctor_id, is_active=True)
        # Patient: use is_active=True (assuming Patient has is_active)
        patient = Patient.objects.get(id=patient_id, is_active=True)
    except (Hospital.DoesNotExist, Doctor.DoesNotExist, Patient.DoesNotExist) as e:
        raise ValidationError(_("One or more related records do not exist or are inactive."))

    # Check doctor belongs to hospital
    if doctor.hospital_id != hospital.id:
        raise ValidationError(_("Doctor does not belong to the specified hospital."))

    # Check doctor availability (no overlapping appointments)
    overlapping = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        deleted_at__isnull=True,
        status__in=['pending', 'confirmed']
    )
    if overlapping.exists():
        raise ValidationError(
            _("The doctor already has an appointment at this date and time.")
        )

    # Generate appointment number and token
    appointment_number = generate_appointment_number()
    token = generate_token(hospital, appointment_date)

    with transaction.atomic():
        appointment = Appointment.objects.create(
            hospital=hospital,
            doctor=doctor,
            patient=patient,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            status='pending',
            appointment_number=appointment_number,
            token=token,
            created_by=created_by,
        )
        return appointment


def generate_token(hospital: Hospital, appointment_date: date) -> str:
    """Generate a unique token for an appointment."""
    last_token = Appointment.objects.filter(
        hospital=hospital,
        appointment_date=appointment_date,
        deleted_at__isnull=True
    ).order_by('-token').values_list('token', flat=True).first()

    if last_token:
        parts = last_token.split('-')
        if len(parts) == 3:
            try:
                seq = int(parts[2]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
    else:
        seq = 1

    hospital_code = getattr(hospital, 'code', f"HOSP{hospital.pk:03d}")
    date_str = appointment_date.strftime('%Y%m%d')
    return f"{hospital_code}-{date_str}-{seq:03d}"


def generate_appointment_number() -> str:
    """Generate a globally unique appointment number."""
    from random import randint
    date_str = timezone.now().strftime('%Y%m%d')
    random_part = f"{randint(100000, 999999)}"
    return f"APPT-{date_str}-{random_part}"


def cancel_appointment(appointment_id: int, cancelled_by=None) -> Appointment:
    try:
        appointment = Appointment.objects.get(id=appointment_id, deleted_at__isnull=True)
    except Appointment.DoesNotExist:
        raise ValidationError(_("Appointment not found."))
    if appointment.status == 'completed':
        raise ValidationError(_("Cannot cancel a completed appointment."))
    if appointment.status == 'cancelled':
        raise ValidationError(_("Appointment is already cancelled."))
    with transaction.atomic():
        Appointment.objects.filter(id=appointment_id).update(
            status='cancelled',
            cancelled_at=timezone.now(),
            cancelled_by=cancelled_by,
        )
        appointment.refresh_from_db()
        return appointment


def confirm_appointment(appointment_id: int, confirmed_by=None) -> Appointment:
    try:
        appointment = Appointment.objects.get(id=appointment_id, deleted_at__isnull=True)
    except Appointment.DoesNotExist:
        raise ValidationError(_("Appointment not found."))
    if appointment.status != 'pending':
        raise ValidationError(_("Only pending appointments can be confirmed."))
    with transaction.atomic():
        Appointment.objects.filter(id=appointment_id).update(
            status='confirmed',
            confirmed_at=timezone.now(),
            confirmed_by=confirmed_by,
        )
        appointment.refresh_from_db()
        return appointment


def complete_appointment(appointment_id: int, completed_by=None) -> Appointment:
    try:
        appointment = Appointment.objects.get(id=appointment_id, deleted_at__isnull=True)
    except Appointment.DoesNotExist:
        raise ValidationError(_("Appointment not found."))
    if appointment.status in ['cancelled', 'completed']:
        raise ValidationError(_("Cannot complete a cancelled or already completed appointment."))
    with transaction.atomic():
        Appointment.objects.filter(id=appointment_id).update(
            status='completed',
            completed_at=timezone.now(),
            completed_by=completed_by,
        )
        appointment.refresh_from_db()
        return appointment


def doctor_available(doctor_id: int, date: date, time: time) -> bool:
    overlapping = Appointment.objects.filter(
        doctor_id=doctor_id,
        appointment_date=date,
        appointment_time=time,
        deleted_at__isnull=True,
        status__in=['pending', 'confirmed']
    )
    return not overlapping.exists()


def dashboard_statistics(doctor_id: Optional[int] = None) -> Dict[str, Any]:
    qs = Appointment.objects.filter(deleted_at__isnull=True)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    total = qs.count()
    pending = qs.filter(status='pending').count()
    confirmed = qs.filter(status='confirmed').count()
    cancelled = qs.filter(status='cancelled').count()
    completed = qs.filter(status='completed').count()
    today = timezone.now().date()
    today_count = qs.filter(appointment_date=today).count()
    return {
        'total': total,
        'pending': pending,
        'confirmed': confirmed,
        'cancelled': cancelled,
        'completed': completed,
        'today': today_count,
    }


def search_appointments(query: str) -> QuerySet:
    if not query:
        return Appointment.objects.none()
    q = Q()
    q |= Q(patient__user__first_name__icontains=query)
    q |= Q(patient__user__last_name__icontains=query)
    q |= Q(doctor__user__first_name__icontains=query)
    q |= Q(doctor__user__last_name__icontains=query)
    q |= Q(hospital__name__icontains=query)
    q |= Q(appointment_number__icontains=query)
    q |= Q(token__icontains=query)
    return Appointment.objects.filter(q, deleted_at__isnull=True).select_related(
        'hospital', 'doctor', 'patient', 'doctor__user', 'patient__user'
    )


def filter_appointments(
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    hospital_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    is_active: bool = True,
) -> QuerySet:
    qs = Appointment.objects.all()
    if is_active:
        qs = qs.filter(deleted_at__isnull=True)
    else:
        qs = qs.filter(deleted_at__isnull=False)
    if status:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(appointment_date__gte=date_from)
    if date_to:
        qs = qs.filter(appointment_date__lte=date_to)
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    return qs.select_related('hospital', 'doctor', 'patient')


def get_patient_appointments(patient_id: int) -> QuerySet:
    return Appointment.objects.filter(
        patient_id=patient_id,
        deleted_at__isnull=True
    ).select_related('hospital', 'doctor').order_by('-appointment_date', '-appointment_time')


def get_doctor_appointments(doctor_id: int, status: Optional[str] = None) -> QuerySet:
    qs = Appointment.objects.filter(
        doctor_id=doctor_id,
        deleted_at__isnull=True
    ).select_related('hospital', 'patient')
    if status:
        qs = qs.filter(status=status)
    return qs.order_by('-appointment_date', '-appointment_time')


def get_upcoming_appointments(doctor_id: Optional[int] = None, days_ahead: int = 7) -> QuerySet:
    today = timezone.now().date()
    future = today + timedelta(days=days_ahead)
    qs = Appointment.objects.filter(
        appointment_date__gte=today,
        appointment_date__lte=future,
        deleted_at__isnull=True,
        status__in=['pending', 'confirmed']
    ).select_related('hospital', 'doctor', 'patient')
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    return qs.order_by('appointment_date', 'appointment_time')


def get_appointment_by_number(appointment_number: str) -> Optional[Appointment]:
    try:
        return Appointment.objects.get(
            appointment_number=appointment_number,
            deleted_at__isnull=True
        )
    except Appointment.DoesNotExist:
        return None


def reschedule_appointment(
    appointment_id: int,
    new_date: date,
    new_time: time,
    rescheduled_by=None,
) -> Appointment:
    appointment = get_appointment_or_404(appointment_id)
    if appointment.status in ['cancelled', 'completed']:
        raise ValidationError(_("Cannot reschedule a cancelled or completed appointment."))
    overlapping = Appointment.objects.filter(
        doctor=appointment.doctor,
        appointment_date=new_date,
        appointment_time=new_time,
        deleted_at__isnull=True,
        status__in=['pending', 'confirmed']
    ).exclude(pk=appointment.pk)
    if overlapping.exists():
        raise ValidationError(_("The doctor is not available at the new time."))
    with transaction.atomic():
        appointment.appointment_date = new_date
        appointment.appointment_time = new_time
        appointment.token = generate_token(appointment.hospital, new_date)
        appointment.save(update_fields=['appointment_date', 'appointment_time', 'token'])
        return appointment


def get_appointment_or_404(appointment_id: int) -> Appointment:
    try:
        return Appointment.objects.get(pk=appointment_id, deleted_at__isnull=True)
    except Appointment.DoesNotExist:
        raise ValidationError(_("Appointment not found."))