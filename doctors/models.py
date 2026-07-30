# doctors/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from hospitals.models import Hospital
import random

User = get_user_model()


class DoctorManager(models.Manager):
    """Custom manager for Doctor model with User-aware queries."""
    
    def get_queryset(self):
        return super().get_queryset().select_related('user')
    
    def active(self):
        """Return only doctors with active User accounts."""
        return self.get_queryset().filter(
            user__isnull=False, 
            user__is_active=True,
            is_active=True
        )
    
    def available_for_booking(self):
        """Return doctors available for patient booking."""
        return self.active().filter(
            is_verified=True,
            is_active=True
        )
    
    def get_by_user(self, user):
        """Get Doctor profile for a User."""
        try:
            return self.get_queryset().get(user=user)
        except self.model.DoesNotExist:
            return None
    
    def create_doctor_with_user(self, user_data, doctor_data):
        """Create both User and Doctor profile atomically."""
        from django.contrib.auth.models import User
        from django.db import transaction
        
        with transaction.atomic():
            # Create User
            user = User.objects.create_user(**user_data)
            user.role = 'doctor'
            user.save()
            
            # Create Doctor profile
            doctor = self.model(
                user=user,
                **doctor_data
            )
            doctor.full_clean()
            doctor.save()
            
            return doctor


class Specialty(models.Model):
    """Doctor specialties like Cardiology, Neurology, etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Specialty'
        verbose_name_plural = 'Specialties'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Doctor(models.Model):
    """
    Doctor professional profile.
    MUST always be linked to a User account for authentication.
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # ---------- Authentication (MANDATORY) ----------
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
        verbose_name='User Account',
        help_text='The Django user account for this doctor. Required.'
    )

    # ---------- Basic Info ----------
    full_name = models.CharField(max_length=150, default='Unknown')
    national_id = models.CharField(max_length=20, unique=True, default='0000000000')
    registration_number = models.CharField(
        max_length=50, unique=True,
        default='000000',
        help_text="BMDC registration number"
    )
    doctor_id = models.CharField(max_length=20, unique=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    date_of_birth = models.DateField(default='2000-01-01')
    phone = models.CharField(max_length=15, default='0000000000')
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(default='')
    city = models.CharField(max_length=100, default='')
    district = models.CharField(max_length=100, default='')
    zip_code = models.CharField(max_length=10, blank=True, default='')

    # ---------- Professional ----------
    specialties = models.ManyToManyField(Specialty, related_name='doctors', blank=True)
    hospital = models.ForeignKey(
        Hospital, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='doctors'
    )
    qualification = models.TextField(
        help_text="Medical qualifications, degrees",
        default=''
    )
    experience = models.PositiveIntegerField(
        default=0, help_text="Years of experience"
    )
    consultation_fee = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0.00, help_text="Consultation fee in BDT"
    )
    available_days = models.CharField(
        max_length=100, blank=True,
        default='',
        help_text="e.g. Mon, Wed, Fri"
    )
    available_time_start = models.TimeField(null=True, blank=True)
    available_time_end = models.TimeField(null=True, blank=True)

    # ---------- Profile ----------
    profile_photo = models.ImageField(upload_to='doctors/', blank=True, null=True)
    bio = models.TextField(blank=True, default='', help_text="Short professional biography")
    
    # ---------- Status ----------
    is_active = models.BooleanField(
        default=True,
        help_text="Doctor is available for appointments"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Doctor has been verified by the system"
    )
    
    # ---------- Timestamps ----------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------- Managers ----------
    objects = DoctorManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Doctor'
        verbose_name_plural = 'Doctors'
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='unique_doctor_user'
            ),
            models.UniqueConstraint(
                fields=['registration_number'],
                name='unique_doctor_registration'
            ),
            models.UniqueConstraint(
                fields=['national_id'],
                name='unique_doctor_national_id'
            )
        ]

    def __str__(self):
        """Return the doctor's display name."""
        if self.full_name and self.full_name != 'Unknown':
            name = self.full_name
        elif self.user and self.user.get_full_name():
            name = self.user.get_full_name()
        elif self.user:
            name = self.user.username
        else:
            name = 'Doctor'
        return f"Dr. {name} ({self.registration_number})"

    def save(self, *args, **kwargs):
        """Validate User link and sync data."""
        # Validate that a User is always linked
        if not self.user:
            raise ValidationError(
                "Every doctor must have a linked User account. "
                "Please create a User account first or use create_doctor_with_user()."
            )
        
        # Generate doctor_id if not set
        if not self.doctor_id:
            self.doctor_id = f"DOC-{random.randint(10000, 99999)}"
        
        # Sync email with User
        if self.email and self.user.email != self.email:
            self.user.email = self.email
            self.user.save()
        
        # Sync full_name with User's first_name/last_name
        if self.full_name and self.full_name != 'Unknown':
            name_parts = self.full_name.split(maxsplit=1)
            if self.user.first_name != name_parts[0]:
                self.user.first_name = name_parts[0]
                self.user.save()
            if len(name_parts) > 1 and self.user.last_name != name_parts[1]:
                self.user.last_name = name_parts[1]
                self.user.save()
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('doctors:detail', kwargs={'pk': self.pk})
    
    @property
    def is_user_active(self):
        """Check if linked User account is active."""
        return self.user.is_active if self.user else False
    
    @property
    def username(self):
        """Get username from linked User."""
        return self.user.username if self.user else None
    
    @property
    def display_name(self):
        """Get the display name for the doctor."""
        if self.full_name and self.full_name != 'Unknown':
            return f"Dr. {self.full_name}"
        elif self.user and self.user.get_full_name():
            return f"Dr. {self.user.get_full_name()}"
        elif self.user:
            return f"Dr. {self.user.username}"
        return "Dr. Unknown"


class DoctorAvailability(models.Model):
    """Doctor's weekly availability schedule."""
    
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_appointments = models.PositiveIntegerField(
        default=10,
        help_text="Maximum appointments in this time slot"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Doctor Availability'
        verbose_name_plural = 'Doctor Availability'
        unique_together = ['doctor', 'day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.display_name} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"
    
    def clean(self):
        """Validate that end_time is after start_time."""
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)