# laboratory/models.py
"""
Laboratory module models for NHIMS.

Contains only the five core models:
- TestCategory
- LaboratoryTest
- LabOrder
- LabOrderItem
- LabResult

All models support soft delete, audit trail, and Django 6 best practices.
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from appointments.models import Appointment
from prescriptions.models import Prescription
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient

User = get_user_model()


class TestCategory(models.Model):
    """
    Category for grouping laboratory tests.
    Examples: Hematology, Biochemistry, Microbiology, etc.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Category Name'),
        db_index=True,
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Inactive categories will not appear in dropdowns.'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At'),
        db_index=True,
        help_text=_('Soft delete timestamp.'),
    )

    class Meta:
        db_table = 'laboratory_testcategory'
        ordering = ['name']
        verbose_name = _('Test Category')
        verbose_name_plural = _('Test Categories')
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_available(self):
        return self.deleted_at is None and self.is_active


class LaboratoryTest(models.Model):
    """
    Master catalogue of laboratory tests with full metadata.
    """
    test_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Test Code'),
        help_text=_('Short code, e.g., CBC, LFT, TSH.'),
        db_index=True,
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_('Test Name'),
        db_index=True,
    )
    category = models.ForeignKey(
        TestCategory,
        on_delete=models.PROTECT,
        related_name='tests',
        verbose_name=_('Category'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Detailed description of the test.'),
    )
    normal_range = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Normal Range'),
        help_text=_('e.g., "4.5–11.0 x10^3/µL" or "Male: 13.5–17.5 g/dL".'),
    )
    unit = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Unit'),
        help_text=_('e.g., mg/dL, µL, IU/L.'),
    )
    sample_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Sample Type'),
        help_text=_('e.g., Blood, Urine, Swab.'),
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_('Price (BDT)'),
        help_text=_('Cost of the test in Bangladeshi Taka.'),
    )
    preparation = models.TextField(
        blank=True,
        verbose_name=_('Preparation Instructions'),
        help_text=_('Special preparation required before the test.'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Inactive tests will not appear in dropdowns.'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At'),
        db_index=True,
        help_text=_('Soft delete timestamp.'),
    )

    class Meta:
        db_table = 'laboratory_test'
        ordering = ['name']
        verbose_name = _('Laboratory Test')
        verbose_name_plural = _('Laboratory Tests')
        indexes = [
            models.Index(fields=['test_code']),
            models.Index(fields=['name']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['deleted_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['test_code'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_test_code'
            )
        ]

    def __str__(self):
        return f"{self.test_code} – {self.name}"

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_available(self):
        return self.deleted_at is None and self.is_active


class LabOrder(models.Model):
    """
    Laboratory order linked to a prescription.
    One order per prescription (OneToOne).
    """
    class Status(models.TextChoices):
        ORDERED = 'ordered', _('Ordered')
        COLLECTED = 'collected', _('Sample Collected')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')

    order_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name=_('Order Number'),
        help_text=_('Auto‑generated unique identifier (LAB-YYYYMMDD-XXXX).'),
        db_index=True,
    )
    prescription = models.OneToOneField(
        Prescription,
        on_delete=models.CASCADE,
        related_name='lab_order',
        verbose_name=_('Prescription'),
        null=True,      # ✅ যোগ করুন
        blank=True,     # ✅ যোগ করুন
        help_text=_('The prescription that generated this lab order.'),
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='lab_orders',
        verbose_name=_('Appointment'),
        editable=False,
        null=True,      # ✅ এই লাইনটি যোগ করুন
        blank=True, 
        help_text=_('Auto‑populated from the prescription.'),
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='lab_orders',
        verbose_name=_('Patient'),
        editable=False,
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='lab_orders',
        verbose_name=_('Doctor'),
        editable=False,
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='lab_orders',
        verbose_name=_('Hospital'),
        editable=False,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ORDERED,
        verbose_name=_('Status'),
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes'),
        help_text=_('Additional notes for the lab technician.'),
    )
    ordered_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Ordered Date'),
        db_index=True,
    )
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
        related_name='lab_orders_created',
        verbose_name=_('Created By'),
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lab_orders_updated',
        verbose_name=_('Updated By'),
    )

    class Meta:
        db_table = 'laboratory_laborder'
        ordering = ['-ordered_date']
        verbose_name = _('Lab Order')
        verbose_name_plural = _('Lab Orders')
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['patient', 'doctor', 'hospital']),
            models.Index(fields=['prescription']),
            models.Index(fields=['deleted_at']),
            models.Index(fields=['ordered_date']),
        ]

    def __str__(self):
        return f"{self.order_number} – {self.patient}"

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_active(self):
        return self.deleted_at is None

    def get_status_display(self):
        return self.Status(self.status).label

    def save(self, *args, **kwargs):
        if getattr(self, 'prescription_id', None):
            prescription = self.prescription
            # Auto-populate from prescription using the raw ID fields
            if not getattr(self, 'appointment_id', None):
                self.appointment = prescription.appointment
            if not getattr(self, 'patient_id', None):
                self.patient = prescription.patient
            if not getattr(self, 'doctor_id', None):
                self.doctor = prescription.doctor
            if not getattr(self, 'hospital_id', None):
                self.hospital = prescription.hospital

        if not self.order_number:
            self.order_number = self.generate_order_number()

        super().save(*args, **kwargs)

    def generate_order_number(self) -> str:
        """Generate a unique order number: LAB-YYYYMMDD-XXXX."""
        today = timezone.now()
        date_part = today.strftime('%Y%m%d')
        count = LabOrder.objects.filter(
            ordered_date__date=today.date()
        ).count() + 1
        seq = str(count).zfill(4)
        return f"LAB-{date_part}-{seq}"


class LabOrderItem(models.Model):
    """
    Individual test item within a lab order.
    """
    lab_order = models.ForeignKey(
        LabOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Lab Order'),
    )
    test = models.ForeignKey(
        LaboratoryTest,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name=_('Laboratory Test'),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes'),
        help_text=_('Special instructions for this test.'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At'),
        db_index=True,
        help_text=_('Soft delete timestamp.'),
    )

    class Meta:
        db_table = 'laboratory_laborderitem'
        ordering = ['pk']
        verbose_name = _('Lab Order Item')
        verbose_name_plural = _('Lab Order Items')
        indexes = [
            models.Index(fields=['lab_order']),
            models.Index(fields=['test']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return f"{self.lab_order.order_number} – {self.test.name}"

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_active(self):
        return self.deleted_at is None


class LabResult(models.Model):
    """
    Result for a specific lab order item.
    Each order item has exactly one result (OneToOne).
    """
    order_item = models.OneToOneField(
        LabOrderItem,
        on_delete=models.CASCADE,
        related_name='result',
        verbose_name=_('Order Item'),
    )
    result = models.TextField(
        blank=True,
        verbose_name=_('Result'),
        help_text=_('Actual result value (e.g., "5.2", "Positive", "Normal").'),
    )
    interpretation = models.TextField(
        blank=True,
        verbose_name=_('Interpretation'),
        help_text=_('Clinical interpretation (e.g., "Normal", "Abnormal").'),
    )
    remarks = models.TextField(
        blank=True,
        verbose_name=_('Remarks'),
        help_text=_('Additional comments from the technician or pathologist.'),
    )
    report_file = models.FileField(
        upload_to='laboratory/reports/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name=_('Report File'),
        help_text=_('Upload PDF, JPEG, or PNG file (max 10 MB).'),
    )
    technician = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lab_results_technician',
        verbose_name=_('Technician'),
        help_text=_('User who entered the result.'),
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lab_results_verified',
        verbose_name=_('Verified By'),
        help_text=_('Doctor or pathologist who verified the result.'),
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Verified At'),
        help_text=_('Time when the result was verified.'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At'),
        db_index=True,
        help_text=_('Soft delete timestamp.'),
    )

    class Meta:
        db_table = 'laboratory_labresult'
        ordering = ['-created_at']
        verbose_name = _('Lab Result')
        verbose_name_plural = _('Lab Results')
        indexes = [
            models.Index(fields=['order_item']),
            models.Index(fields=['technician']),
            models.Index(fields=['verified_by']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return f"Result for {self.order_item.test.name} ({self.order_item.lab_order.order_number})"

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_active(self):
        return self.deleted_at is None

    def clean(self):
        # Optionally enforce validation: cannot have result without order_item being active? We'll skip.
        pass