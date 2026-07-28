# prescriptions/models.py
"""
Prescription models for NHIMS.

A prescription is linked to a single completed appointment.
Includes prescription details, medicine items, audit trail, and soft delete.
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q

from appointments.models import Appointment
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient

User = get_user_model()


class Prescription(models.Model):
    """
    A medical prescription issued after a completed appointment.

    Linked one‑to‑one with Appointment. Automatically populates
    hospital, doctor, and patient from the appointment.
    """

    # ---------- Status Choices ----------
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        ISSUED = 'issued', _('Issued')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')

    # ---------- Core Fields ----------
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='prescription',
        verbose_name=_('Appointment'),
        help_text=_('The completed appointment for this prescription.'),
    )

    # Auto‑populated from appointment
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name=_('Hospital'),
        editable=False,
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name=_('Doctor'),
        editable=False,
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name=_('Patient'),
        editable=False,
    )

    # ---------- Prescription Content ----------
    diagnosis = models.TextField(
        verbose_name=_('Diagnosis'),
        help_text=_('Medical diagnosis based on the appointment.'),
    )
    symptoms = models.TextField(
        blank=True,
        verbose_name=_('Symptoms'),
        help_text=_('Symptoms reported by the patient.'),
    )
    clinical_notes = models.TextField(
        blank=True,
        verbose_name=_('Clinical Notes'),
        help_text=_('Additional clinical observations and notes.'),
    )
    advice = models.TextField(
        blank=True,
        verbose_name=_('Advice'),
        help_text=_('General advice and recommendations for the patient.'),
    )

    # ---------- Follow‑up ----------
    follow_up_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Follow-up Date'),
        help_text=_('Scheduled follow‑up date, if any.'),
    )

    # ---------- Status & Identifiers ----------
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status'),
        db_index=True,
    )
    prescription_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name=_('Prescription Number'),
        help_text=_('Auto‑generated unique identifier (e.g., RX-202600001).'),
    )

    # ---------- Digital Signature & QR ----------
    doctor_signature = models.TextField(
        blank=True,
        verbose_name=_('Doctor Signature'),
        help_text=_('Digital signature or verification token.'),
    )
    qr_code = models.TextField(
        blank=True,
        verbose_name=_('QR Code'),
        help_text=_('QR code data for verification.'),
    )

    # ---------- Audit Trail ----------
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At'),
        db_index=True,
        help_text=_('Soft delete timestamp.'),
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions_created',
        verbose_name=_('Created By'),
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions_updated',
        verbose_name=_('Updated By'),
    )

    # ---------- Meta ----------
    class Meta:
        db_table = 'prescriptions_prescription'
        verbose_name = _('Prescription')
        verbose_name_plural = _('Prescriptions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['prescription_number']),
            models.Index(fields=['status']),
            models.Index(fields=['appointment']),
            models.Index(fields=['hospital', 'doctor', 'patient']),
            models.Index(fields=['created_at']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return f"{self.prescription_number} – {self.patient} ({self.get_status_display()})"

    # ---------- Soft Delete ----------
    def delete(self, using=None, keep_parents=False):
        """Soft delete instead of hard delete."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the record."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft‑deleted prescription."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_active(self):
        return self.deleted_at is None

    # ---------- Validation ----------
    def clean(self):
        """
        Validate business rules and auto‑populate from appointment.
        """
        # 1. Appointment must exist and be completed
        if not self.appointment_id:
            raise ValidationError(_('Appointment is required.'))

        # Fetch appointment (if not already cached)
        if not hasattr(self, '_appointment_cached'):
            try:
                self._appointment = Appointment.objects.select_related(
                    'hospital', 'doctor', 'patient'
                ).get(
                    pk=self.appointment_id,
                    deleted_at__isnull=True
                )
                self._appointment_cached = True
            except Appointment.DoesNotExist:
                raise ValidationError(_('Appointment not found or has been deleted.'))

        appointment = self._appointment

        # 2. Appointment must be completed
        if appointment.status != Appointment.Status.COMPLETED:
            raise ValidationError(
                _('Prescription can only be created for a completed appointment.')
            )

        # 3. Auto‑populate hospital, doctor, patient from appointment
        if not self.hospital_id:
            self.hospital = appointment.hospital
        if not self.doctor_id:
            self.doctor = appointment.doctor
        if not self.patient_id:
            self.patient = appointment.patient

        # 4. Check if already has a prescription (except when updating itself)
        if not self.pk:
            if hasattr(appointment, 'prescription'):
                raise ValidationError(
                    _('A prescription already exists for this appointment.')
                )

        # 5. Ensure the auto‑populated fields match the appointment
        if self.hospital_id and self.hospital_id != appointment.hospital_id:
            raise ValidationError(
                _('Hospital must match the appointment’s hospital.')
            )
        if self.doctor_id and self.doctor_id != appointment.doctor_id:
            raise ValidationError(
                _('Doctor must match the appointment’s doctor.')
            )
        if self.patient_id and self.patient_id != appointment.patient_id:
            raise ValidationError(
                _('Patient must match the appointment’s patient.')
            )

        # 6. Follow‑up date must be in the future (if provided)
        if self.follow_up_date and self.follow_up_date < timezone.now().date():
            raise ValidationError(
                _('Follow‑up date cannot be in the past.')
            )

    def save(self, *args, **kwargs):
        """
        Auto‑populate fields from appointment, generate number, and enforce clean.
        """
        if self.appointment_id:
            # Auto‑populate from appointment (if not already set)
            if not self.hospital_id:
                self.hospital = self.appointment.hospital
            if not self.doctor_id:
                self.doctor = self.appointment.doctor
            if not self.patient_id:
                self.patient = self.appointment.patient

        # Generate prescription number if missing
        if not self.prescription_number:
            self.prescription_number = self.generate_number()

        self.full_clean()
        super().save(*args, **kwargs)

    def generate_number(self) -> str:
        """
        Generate a unique prescription number: RX-YYYYMMDD-XXXX
        where XXXX is a zero‑padded sequential number for the day.
        """
        today = timezone.now()
        date_part = today.strftime('%Y%m%d')
        # Count prescriptions created today (including soft‑deleted ones? we count all)
        count = Prescription.objects.filter(
            created_at__date=today.date()
        ).count() + 1
        seq = str(count).zfill(4)
        return f"RX-{date_part}-{seq}"

    # ---------- Helper Methods ----------
    def get_status_display(self):
        return self.Status(self.status).label

    def is_draft(self):
        return self.status == self.Status.DRAFT

    def is_issued(self):
        return self.status == self.Status.ISSUED

    def is_completed(self):
        return self.status == self.Status.COMPLETED

    def is_cancelled(self):
        return self.status == self.Status.CANCELLED


class PrescriptionMedicine(models.Model):
    """
    Individual medicine item within a prescription.
    """

    # ---------- Route Choices ----------
    class Route(models.TextChoices):
        ORAL = 'oral', _('Oral')
        TOPICAL = 'topical', _('Topical')
        INJECTION = 'injection', _('Injection')
        INHALATION = 'inhalation', _('Inhalation')
        SUPPOSITORY = 'suppository', _('Suppository')
        OTHER = 'other', _('Other')

    # ---------- Frequency Choices (simplified) ----------
    class Frequency(models.TextChoices):
        ONCE = 'once', _('Once daily')
        TWICE = 'twice', _('Twice daily')
        THREE = 'three', _('Three times daily')
        FOUR = 'four', _('Four times daily')
        AS_NEEDED = 'as_needed', _('As needed')
        OTHER = 'other', _('Other')

    # ---------- Timing Flags (for convenience) ----------
    before_food = models.BooleanField(default=False, verbose_name=_('Before Food'))
    after_food = models.BooleanField(default=False, verbose_name=_('After Food'))
    morning = models.BooleanField(default=False, verbose_name=_('Morning'))
    afternoon = models.BooleanField(default=False, verbose_name=_('Afternoon'))
    night = models.BooleanField(default=False, verbose_name=_('Night'))

    # ---------- Core Fields ----------
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='medicines',
        verbose_name=_('Prescription'),
    )
    medicine_name = models.CharField(
        max_length=255,
        verbose_name=_('Medicine Name'),
        help_text=_('Generic or brand name of the medicine.'),
    )
    dosage = models.CharField(
        max_length=100,
        verbose_name=_('Dosage'),
        help_text=_('e.g., 500 mg, 1 tablet, 5 ml.'),
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.ONCE,
        verbose_name=_('Frequency'),
    )
    duration = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Duration'),
        help_text=_('e.g., 7 days, 2 weeks, as needed.'),
    )
    route = models.CharField(
        max_length=20,
        choices=Route.choices,
        default=Route.ORAL,
        verbose_name=_('Route'),
    )
    instruction = models.TextField(
        blank=True,
        verbose_name=_('Instruction'),
        help_text=_('Additional instructions for the patient.'),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes'),
        help_text=_('Internal notes for the pharmacist or doctor.'),
    )

    class Meta:
        db_table = 'prescriptions_medicine'
        verbose_name = _('Medicine')
        verbose_name_plural = _('Medicines')
        ordering = ['pk']

    def __str__(self):
        return f"{self.medicine_name} ({self.dosage})"

    def clean(self):
        # No strict validation, but we can add if needed.
        pass