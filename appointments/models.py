# appointments/models.py
"""
Appointment model for the NHIMS system.

Manages patient appointments with doctors, including scheduling,
status tracking, soft delete, and audit trail.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()


class Appointment(models.Model):
    """
    Represents a scheduled appointment between a patient and a doctor.
    Includes full audit trail and soft delete support.
    """

    # ---------- Status Choices ----------
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        CANCELLED = 'cancelled', _('Cancelled')
        COMPLETED = 'completed', _('Completed')

    # ---------- Core Fields ----------
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name=_('Hospital'),
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name=_('Doctor'),
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name=_('Patient'),
    )

    appointment_date = models.DateField(
        verbose_name=_('Appointment Date'),
        help_text=_('Date of the appointment.'),
    )
    appointment_time = models.TimeField(
        verbose_name=_('Appointment Time'),
        help_text=_('Time of the appointment.'),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Status'),
        db_index=True,
    )

    reason = models.TextField(
        blank=True,
        verbose_name=_('Reason'),
        help_text=_('Reason for the appointment (optional).'),
    )

    # ---------- Unique Identifiers ----------
    appointment_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name=_('Appointment Number'),
        help_text=_('Unique human-readable appointment number.'),
    )
    token = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name=_('Token'),
        help_text=_('Hospital-specific token for the appointment.'),
    )

    # ---------- Audit Trail ----------
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Deleted At'),
        db_index=True, help_text=_('Soft delete timestamp.')
    )

    # ---------- Action Timestamps & Users ----------
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appointments_created', verbose_name=_('Created By')
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Confirmed At'))
    confirmed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appointments_confirmed', verbose_name=_('Confirmed By')
    )
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Cancelled At'))
    cancelled_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appointments_cancelled', verbose_name=_('Cancelled By')
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At'))
    completed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appointments_completed', verbose_name=_('Completed By')
    )
    rescheduled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Rescheduled At'))
    rescheduled_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appointments_rescheduled', verbose_name=_('Rescheduled By')
    )

    class Meta:
        db_table = 'appointments_appointment'
        verbose_name = _('Appointment')
        verbose_name_plural = _('Appointments')
        ordering = ['-appointment_date', '-appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'status']),
            models.Index(fields=['appointment_number']),
            models.Index(fields=['token']),
            models.Index(fields=['deleted_at']),
        ]
        unique_together = [
            ['doctor', 'appointment_date', 'appointment_time'],
        ]

    def __str__(self):
        return f"{self.appointment_number} - {self.patient} with {self.doctor} on {self.appointment_date}"

    # ---------- Soft Delete ----------
    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_active(self):
        return self.deleted_at is None

    # ---------- Clean / Validation ----------
    def clean(self):
        """
        Validate that:
        - Appointment date is not in the past (allow today).
        - Doctor belongs to the selected hospital.
        - No overlapping appointments for the same doctor (unless current instance).
        """
        # Date validation
        if self.appointment_date and self.appointment_date < timezone.now().date():
            raise ValidationError(_('Appointment date cannot be in the past.'))

        # Doctor-Hospital relationship: use _id fields to avoid RelatedObjectDoesNotExist
        doctor_id = getattr(self, 'doctor_id', None)
        hospital_id = getattr(self, 'hospital_id', None)

        if doctor_id and hospital_id:
            if not Doctor.objects.filter(
                pk=doctor_id,
                hospital=hospital_id,
            ).exists():
                raise ValidationError(_('Doctor does not belong to the selected hospital.'))

        # Doctor availability – check only if doctor_id, date, and time are present
        if doctor_id and self.appointment_date and self.appointment_time:
            overlapping = Appointment.objects.filter(
                doctor_id=doctor_id,
                appointment_date=self.appointment_date,
                appointment_time=self.appointment_time,
                deleted_at__isnull=True  # Only active (not soft-deleted) appointments
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(
                    _('The doctor already has an appointment at this date and time.')
                )

            # Optional: enforce working hours (9 AM – 5 PM)
            if self.appointment_time < timezone.datetime.strptime('09:00', '%H:%M').time() or \
               self.appointment_time > timezone.datetime.strptime('17:00', '%H:%M').time():
                raise ValidationError(
                    _('Appointment time must be between 09:00 AM and 05:00 PM.')
                )

        # Ensure patient is active (if the model has is_active)
            patient_id = getattr(self, 'patient_id', None)
            patient = getattr(self, 'patient', None) if patient_id else None
            if patient is not None and hasattr(patient, 'is_active') and not patient.is_active:
                raise ValidationError(_('The selected patient is inactive.'))

    # ---------- Save Override ----------
    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.appointment_number:
            from .services import generate_appointment_number
            self.appointment_number = generate_appointment_number()
        if not self.token and self.hospital:
            from .services import generate_token
            self.token = generate_token(self.hospital, self.appointment_date)
        super().save(*args, **kwargs)

    def get_status_display(self):
        return self.Status(self.status).label

    def is_pending(self):
        return self.status == self.Status.PENDING

    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED

    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    def is_completed(self):
        return self.status == self.Status.COMPLETED
    