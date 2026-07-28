from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from .validators import validate_phone, validate_email, validate_website, validate_latitude, validate_longitude
import uuid

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