from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from .validators import validate_phone, validate_email, validate_website, validate_latitude, validate_longitude
import uuid
from django.core.validators import RegexValidator

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
User = get_user_model()


class HospitalType(models.TextChoices):
    GOVERNMENT = 'gov', 'Government'
    PRIVATE = 'private', 'Private'
    NGO = 'ngo', 'NGO'
    MILITARY = 'military', 'Military'
    MEDICAL_COLLEGE = 'medical_college', 'Medical College'
    CLINIC = 'clinic', 'Clinic'
    DIAGNOSTIC = 'diagnostic', 'Diagnostic Center'
    SPECIALIZED = 'specialized', 'Specialized Hospital'


class Ownership(models.TextChoices):
    PUBLIC = 'public', 'Public'
    PRIVATE_OWNED = 'private_owned', 'Private Owned'
    TRUST = 'trust', 'Trust'
    PARTNERSHIP = 'partnership', 'Partnership'


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_created'
    )

    class Meta:
        abstract = True


class Hospital(BaseModel):
    # Basic Info
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    hospital_code = models.CharField(max_length=20, unique=True, blank=True)
    registration_number = models.CharField(max_length=100, unique=True)
    license_number = models.CharField(max_length=100, blank=True)
    tin = models.CharField(max_length=50, blank=True, help_text="Tax Identification Number")
    bin = models.CharField(max_length=50, blank=True, help_text="Business Identification Number")
    hospital_type = models.CharField(max_length=20, choices=HospitalType.choices, default=HospitalType.PRIVATE)
    ownership = models.CharField(max_length=20, choices=Ownership.choices, default=Ownership.PRIVATE_OWNED)
    established_year = models.PositiveIntegerField(null=True, blank=True)

    # Description
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    history = models.TextField(blank=True)

    # Logo & Images
    logo = models.ImageField(upload_to='hospitals/logos/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='hospitals/covers/', blank=True, null=True)

    # Address
    country = models.CharField(max_length=100, default='Bangladesh')
    division = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    upazila = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    full_address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[validate_latitude])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[validate_longitude])
    google_map_link = models.URLField(blank=True)

    # Contact
    email = models.EmailField(validators=[validate_email])
    phone = models.CharField(max_length=20, validators=[validate_phone])
    emergency_phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    ambulance_phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    website = models.URLField(blank=True, validators=[validate_website])

    # Social Media
    facebook = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    youtube = models.URLField(blank=True)

    # Facilities (checkboxes)
    emergency_available = models.BooleanField(default=False)
    icu = models.BooleanField(default=False, help_text="Intensive Care Unit")
    nicu = models.BooleanField(default=False, help_text="Neonatal ICU")
    ccu = models.BooleanField(default=False, help_text="Cardiac Care Unit")
    emergency_department = models.BooleanField(default=False)
    operation_theater = models.BooleanField(default=False)
    laboratory = models.BooleanField(default=False)
    radiology = models.BooleanField(default=False)
    mri = models.BooleanField(default=False)
    ct_scan = models.BooleanField(default=False)
    x_ray = models.BooleanField(default=False)
    ultrasound = models.BooleanField(default=False)
    blood_bank = models.BooleanField(default=False)
    pharmacy = models.BooleanField(default=False)
    vaccination_center = models.BooleanField(default=False)
    dialysis = models.BooleanField(default=False)
    cancer_unit = models.BooleanField(default=False)
    burn_unit = models.BooleanField(default=False)
    heart_center = models.BooleanField(default=False)
    eye_center = models.BooleanField(default=False)
    dental_unit = models.BooleanField(default=False)

    # Amenities
    parking = models.BooleanField(default=False)
    wheelchair_access = models.BooleanField(default=False)
    prayer_room = models.BooleanField(default=False)
    cafeteria = models.BooleanField(default=False)
    atm = models.BooleanField(default=False)
    wifi = models.BooleanField(default=False)
    generator_backup = models.BooleanField(default=False)
    oxygen_plant = models.BooleanField(default=False)
    open_24_hours = models.BooleanField(default=False)

    # Statistics
    total_doctors = models.PositiveIntegerField(default=0)
    total_nurses = models.PositiveIntegerField(default=0)
    total_beds = models.PositiveIntegerField(default=0)
    available_beds = models.PositiveIntegerField(default=0)
    icu_beds = models.PositiveIntegerField(default=0)
    emergency_beds = models.PositiveIntegerField(default=0)

    # Rating
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)

    # Status
    verified = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['hospital_code']),
            models.Index(fields=['district', 'division']),
            models.Index(fields=['hospital_type']),
            models.Index(fields=['verified', 'featured']),
        ]
        verbose_name = 'Hospital'
        verbose_name_plural = 'Hospitals'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.hospital_code:
            # Generate a unique code: HOSP-YYYY-XXXX
            import random
            self.hospital_code = f"HOSP-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('hospitals:detail', kwargs={'slug': self.slug})

    @property
    def rating_stars(self):
        return round(self.average_rating * 2) / 2

    @property
    def is_emergency_ready(self):
        return self.emergency_available or self.emergency_department


class HospitalDepartment(BaseModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    head_doctor = models.ForeignKey(
        'doctors.Doctor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='headed_departments'
    )
    floor_number = models.PositiveIntegerField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, validators=[validate_phone])
    email = models.EmailField(blank=True, validators=[validate_email])
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        unique_together = ['hospital', 'name']

    def __str__(self):
        return f"{self.name} ({self.hospital.name})"


class HospitalFacility(BaseModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='facilities')
    title = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class, e.g. 'fas fa-ambulance'")
    description = models.TextField(blank=True)
    available = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __str__(self):
        return self.title


class HospitalGallery(BaseModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='hospitals/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Gallery Image'
        verbose_name_plural = 'Gallery Images'

    def __str__(self):
        return f"{self.hospital.name} - {self.caption or 'Image'}"
    

class HospitalReview(BaseModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='reviews')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='hospital_reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review = models.TextField()
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def __str__(self):
        return f"{self.patient.full_name} - {self.rating}★"


class HospitalOperatingHour(BaseModel):
    DAY_CHOICES = [
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ]
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='operating_hours')
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_emergency = models.BooleanField(default=False)

    class Meta:
        ordering = ['day']
        unique_together = ['hospital', 'day']
        verbose_name = 'Operating Hour'
        verbose_name_plural = 'Operating Hours'

    def __str__(self):
        return f"{self.get_day_display()}: {self.open_time} - {self.close_time}"
    
class HospitalApplication(models.Model):
    """
    Hospital Application Model.
    Stores hospital registration applications submitted by Hospital Admins.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SUBMITTED = 'submitted', _('Submitted')
        UNDER_REVIEW = 'under_review', _('Under Review')
        NEED_MORE_INFO = 'need_more_info', _('Need More Information')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        WITHDRAWN = 'withdrawn', _('Withdrawn')
    
    class HospitalType(models.TextChoices):
        GENERAL = 'general', _('General Hospital')
        PRIVATE = 'private', _('Private Hospital')
        GOVERNMENT = 'government', _('Government Hospital')
        MEDICAL_COLLEGE = 'medical_college', _('Medical College Hospital')
        CLINIC = 'clinic', _('Clinic')
        DIAGNOSTIC = 'diagnostic', _('Diagnostic Center')
        DENTAL = 'dental', _('Dental Clinic')
        EYE = 'eye', _('Eye Hospital')
        MENTAL_HEALTH = 'mental_health', _('Mental Health Hospital')
        NGO = 'ngo', _('NGO Hospital')
        SPECIALIZED = 'specialized', _('Specialized Hospital')
    
    # System Fields
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('Application ID')
    )
    
    application_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name=_('Application Number'),
        db_index=True,
    )
    
    # Relationships
    hospital_admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hospital_applications',
        # limit_choices_to={'role': 'hospital_admin'},
        verbose_name=_('Hospital Admin'),
    )
    
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications',
        verbose_name=_('Reviewed By'),
    )
    
    # Basic Information
    hospital_name = models.CharField(
        max_length=200,
        verbose_name=_('Hospital Name'),
        db_index=True,
    )
    
    hospital_type = models.CharField(
        max_length=50,
        choices=HospitalType.choices,
        default=HospitalType.GENERAL,
        verbose_name=_('Hospital Type'),
    )
    
    license_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('License Number'),
        db_index=True,
    )
    
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Registration Number'),
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Hospital Description'),
    )
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^01[3-9]\d{8}$',
        message='Enter a valid Bangladesh phone number (e.g., 017XXXXXXXX)'
    )
    
    hospital_email = models.EmailField(
        unique=True,
        verbose_name=_('Hospital Email'),
    )
    
    phone = models.CharField(
        max_length=15,
        validators=[phone_regex],
        verbose_name=_('Phone Number'),
    )
    
    emergency_phone = models.CharField(
        max_length=15,
        validators=[phone_regex],
        blank=True,
        verbose_name=_('Emergency Phone'),
    )
    
    website = models.URLField(
        blank=True,
        verbose_name=_('Website'),
    )
    
    # Address
    division = models.CharField(
        max_length=50,
        verbose_name=_('Division'),
    )
    
    district = models.CharField(
        max_length=50,
        verbose_name=_('District'),
    )
    
    upazila = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Upazila'),
    )
    
    area = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Area'),
    )
    
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Postal Code'),
    )
    
    full_address = models.TextField(
        verbose_name=_('Full Address'),
    )
    
    google_map_link = models.URLField(
        blank=True,
        verbose_name=_('Google Map Link'),
    )
    
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name=_('Latitude'),
    )
    
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        verbose_name=_('Longitude'),
    )
    
    # Administrator Information
    admin_name = models.CharField(
        max_length=150,
        verbose_name=_('Administrator Name'),
    )
    
    admin_email = models.EmailField(
        verbose_name=_('Administrator Email'),
    )
    
    admin_phone = models.CharField(
        max_length=15,
        validators=[phone_regex],
        verbose_name=_('Administrator Phone'),
    )
    
    admin_designation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Designation'),
    )
    
    # Documents
    logo = models.ImageField(
        upload_to='hospital_applications/logos/',
        blank=True,
        null=True,
        verbose_name=_('Hospital Logo'),
    )
    
    trade_license = models.FileField(
        upload_to='hospital_applications/documents/',
        blank=True,
        null=True,
        verbose_name=_('Trade License'),
    )
    
    hospital_license = models.FileField(
        upload_to='hospital_applications/documents/',
        blank=True,
        null=True,
        verbose_name=_('Hospital License'),
    )
    
    govt_approval = models.FileField(
        upload_to='hospital_applications/documents/',
        blank=True,
        null=True,
        verbose_name=_('Government Approval'),
    )
    
    tin_certificate = models.FileField(
        upload_to='hospital_applications/documents/',
        blank=True,
        null=True,
        verbose_name=_('TIN Certificate'),
    )
    
    other_documents = models.FileField(
        upload_to='hospital_applications/documents/',
        blank=True,
        null=True,
        verbose_name=_('Other Documents'),
    )
    
    # Status & Remarks
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status'),
        db_index=True,
    )
    
    admin_remarks = models.TextField(
        blank=True,
        verbose_name=_('Admin Remarks'),
    )
    
    # Verification Fields
    terms_accepted = models.BooleanField(
        default=False,
        verbose_name=_('Terms Accepted'),
    )
    
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_('Email Verified'),
    )
    
    phone_verified = models.BooleanField(
        default=False,
        verbose_name=_('Phone Verified'),
    )
    
    hospital_verified = models.BooleanField(
        default=False,
        verbose_name=_('Hospital Verified'),
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
    )
    
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Submitted At'),
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Reviewed At'),
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Approved At'),
    )
    
    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Rejected At'),
    )
    
    class Meta:
        db_table = 'hospitals_hospitalapplication'
        verbose_name = _('Hospital Application')
        verbose_name_plural = _('Hospital Applications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['hospital_name']),
            models.Index(fields=['license_number']),
            models.Index(fields=['application_number']),
            models.Index(fields=['hospital_admin', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.hospital_name} ({self.application_number})"
    
    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = self.generate_application_number()
        super().save(*args, **kwargs)
    
    def generate_application_number(self) -> str:
        """Generate unique application number: HAPP-YYYYMMDD-XXXX"""
        today = timezone.now()
        date_part = today.strftime('%Y%m%d')
        count = HospitalApplication.objects.filter(
            created_at__date=today.date()
        ).count() + 1
        seq = str(count).zfill(4)
        return f"HAPP-{date_part}-{seq}"
    
class Room(models.Model):
    """Room/Unit model for hospital departments."""
    
    class RoomType(models.TextChoices):
        GENERAL_WARD = 'general_ward', 'General Ward'
        PRIVATE_CABIN = 'private_cabin', 'Private Cabin'
        VIP_CABIN = 'vip_cabin', 'VIP Cabin'
        ICU = 'icu', 'ICU'
        NICU = 'nicu', 'NICU'
        CCU = 'ccu', 'CCU'
        OPERATION_THEATER = 'operation_theater', 'Operation Theater'
        EMERGENCY_ROOM = 'emergency_room', 'Emergency Room'
        CONSULTATION_ROOM = 'consultation_room', 'Consultation Room'
        LABORATORY = 'laboratory', 'Laboratory'
        PHARMACY = 'pharmacy', 'Pharmacy'
        RECEPTION = 'reception', 'Reception'
        WAITING_AREA = 'waiting_area', 'Waiting Area'
    
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        OCCUPIED = 'occupied', 'Occupied'
        MAINTENANCE = 'maintenance', 'Maintenance'
        INACTIVE = 'inactive', 'Inactive'
    
    # Relationships
    hospital = models.ForeignKey(
        'Hospital',
        on_delete=models.CASCADE,
        related_name='rooms'
    )
    department = models.ForeignKey(
        'HospitalDepartment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rooms'
    )
    
    # Basic Info
    room_number = models.CharField(max_length=50)
    room_type = models.CharField(max_length=30, choices=RoomType.choices, default=RoomType.GENERAL_WARD)
    floor = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    
    # Capacity
    capacity = models.PositiveIntegerField(default=1)
    occupied = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    is_active = models.BooleanField(default=True)
    
    # Additional Info
    assigned_doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_rooms'
    )
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='room_created'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='room_updated'
    )
    
    class Meta:
        ordering = ['department__name', 'room_number']
        unique_together = ['hospital', 'room_number']
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'
    
    def __str__(self):
        return f"{self.room_number} - {self.get_room_type_display()}"
    
    @property
    def available_beds(self):
        return self.capacity - self.occupied
    
    @property
    def is_full(self):
        return self.occupied >= self.capacity
    
    @property
    def occupancy_percentage(self):
        if self.capacity == 0:
            return 0
        return round((self.occupied / self.capacity) * 100)