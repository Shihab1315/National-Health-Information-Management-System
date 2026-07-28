from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital
from appointments.models import Appointment
from prescriptions.models import Prescription

User = get_user_model()


class MedicalRecord(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_records'
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    lab_order = models.ForeignKey(
        'laboratory.LabOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )

    visit_date = models.DateTimeField(default=timezone.now)

    chief_complaint = models.TextField()

    symptoms = models.TextField(blank=True)

    history_of_present_illness = models.TextField(
        blank=True,
        help_text="Detailed description of current illness"
    )

    diagnosis = models.TextField()

    clinical_findings = models.TextField(blank=True)

    blood_pressure_systolic = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    blood_pressure_diastolic = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    pulse = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="beats per minute"
    )

    temperature = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="in °F"
    )

    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="in cm"
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="in kg"
    )

    bmi = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    oxygen_saturation = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="%"
    )

    respiratory_rate = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="breaths per minute"
    )

    treatment_plan = models.TextField(blank=True)

    doctor_notes = models.TextField(blank=True)

    follow_up_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_medical_records'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Medical Record'
        verbose_name_plural = 'Medical Records'

        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['doctor']),
            models.Index(fields=['hospital']),
            models.Index(fields=['appointment']),
            models.Index(fields=['prescription']),
            models.Index(fields=['lab_order']),
            models.Index(fields=['visit_date']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"Record for {self.patient.full_name} - {self.visit_date.strftime('%Y-%m-%d')}"

    @property
    def bmi_value(self):
        if self.height and self.weight:
            height_m = self.height / 100
            if height_m > 0:
                return round(self.weight / (height_m ** 2), 2)
        return None

    def clean(self):
        if (
            self.visit_date
            and self.follow_up_date
            and self.follow_up_date < self.visit_date.date()
        ):
            raise ValidationError({
                "follow_up_date": _(
                    "Follow-up date cannot be before visit date."
                )
            })

        if (
            self.blood_pressure_systolic
            and self.blood_pressure_diastolic
            and self.blood_pressure_systolic <= self.blood_pressure_diastolic
        ):
            raise ValidationError({
                "blood_pressure_systolic": _(
                    "Systolic blood pressure must be greater than diastolic pressure."
                )
            })

        if self.pulse and not (30 <= self.pulse <= 200):
            raise ValidationError({
                "pulse": _("Pulse must be between 30 and 200 bpm.")
            })

        if self.temperature and not (95 <= self.temperature <= 105):
            raise ValidationError({
                "temperature": _("Temperature must be between 95°F and 105°F.")
            })

        if self.oxygen_saturation and not (0 <= self.oxygen_saturation <= 100):
            raise ValidationError({
                "oxygen_saturation": _(
                    "Oxygen saturation must be between 0 and 100."
                )
            })

        if self.respiratory_rate and not (5 <= self.respiratory_rate <= 40):
            raise ValidationError({
                "respiratory_rate": _(
                    "Respiratory rate must be between 5 and 40."
                )
            })
class Allergy(models.Model):
    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_allergies'
    )

    allergen = models.CharField(max_length=200)

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='mild'
    )

    reaction = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    recorded_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'Allergy'
        verbose_name_plural = 'Allergies'

        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['severity']),
            models.Index(fields=['recorded_at']),
        ]

    def __str__(self):
        return f"{self.patient.full_name} - {self.allergen}"


class ChronicDisease(models.Model):
    DISEASE_CHOICES = [
        ('diabetes', 'Diabetes'),
        ('hypertension', 'Hypertension'),
        ('asthma', 'Asthma'),
        ('heart_disease', 'Heart Disease'),
        ('kidney_disease', 'Kidney Disease'),
        ('cancer', 'Cancer'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_chronic_diseases'
    )

    disease = models.CharField(
        max_length=20,
        choices=DISEASE_CHOICES
    )

    diagnosed_date = models.DateField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-diagnosed_date']
        verbose_name = 'Chronic Disease'
        verbose_name_plural = 'Chronic Diseases'

        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['disease']),
            models.Index(fields=['diagnosed_date']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        disease_label = dict(self.DISEASE_CHOICES).get(
            self.disease,
            self.disease
        )
        return f"{self.patient.full_name} - {disease_label}"


class PastHistory(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_past_histories'
    )

    surgeries = models.TextField(
        blank=True,
        help_text="List previous surgeries with dates"
    )

    hospital_admissions = models.TextField(
        blank=True,
        help_text="List previous admissions with details"
    )

    family_history = models.TextField(
        blank=True,
        help_text="Family medical history (diabetes, heart disease, etc.)"
    )

    smoking_status = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('never', 'Never'),
            ('former', 'Former'),
            ('current', 'Current')
        ]
    )

    alcohol_consumption = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('never', 'Never'),
            ('occasional', 'Occasional'),
            ('regular', 'Regular')
        ]
    )

    occupation = models.CharField(
        max_length=100,
        blank=True
    )

    notes = models.TextField(blank=True)

    recorded_at = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Past History'
        verbose_name_plural = 'Past Histories'

        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['recorded_at']),
        ]

    def __str__(self):
        return f"History for {self.patient.full_name}"
class Vaccination(models.Model):
    VACCINE_CHOICES = [
        ('covid', 'COVID-19'),
        ('hepatitis', 'Hepatitis'),
        ('tetanus', 'Tetanus'),
        ('influenza', 'Influenza'),
        ('mmr', 'MMR'),
        ('polio', 'Polio'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_vaccinations'
    )

    vaccine = models.CharField(
        max_length=20,
        choices=VACCINE_CHOICES
    )

    custom_vaccine_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="If 'Other' selected"
    )

    dose_number = models.PositiveIntegerField(default=1)

    administration_date = models.DateField()

    next_due_date = models.DateField(
        null=True,
        blank=True
    )

    administered_by = models.CharField(
        max_length=200,
        blank=True
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-administration_date']
        verbose_name = 'Vaccination'
        verbose_name_plural = 'Vaccinations'

        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['vaccine']),
            models.Index(fields=['administration_date']),
        ]

    def __str__(self):
        vaccine_label = dict(self.VACCINE_CHOICES).get(
            self.vaccine,
            self.vaccine
        )
        return f"{self.patient.full_name} - {vaccine_label} ({self.dose_number})"


class Attachment(models.Model):
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name='attachments'
    )

    file = models.FileField(
        upload_to='medical_records/attachments/'
    )

    description = models.CharField(
        max_length=200,
        blank=True
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_attachments'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'

        indexes = [
            models.Index(fields=['medical_record']),
            models.Index(fields=['uploaded_at']),
        ]

    def __str__(self):
        return f"Attachment for {self.medical_record.patient.full_name}"


class FollowUp(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    ]

    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name='follow_ups'
    )

    scheduled_date = models.DateTimeField()

    completed_date = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )

    notes = models.TextField(blank=True)

    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['scheduled_date']
        verbose_name = 'Follow Up'
        verbose_name_plural = 'Follow Ups'

        indexes = [
            models.Index(fields=['medical_record']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return (
            f"Follow-up for {self.medical_record.patient.full_name} - "
            f"{self.scheduled_date.strftime('%Y-%m-%d')}"
        )