# doctors/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from hospitals.models import Hospital
import random

User = get_user_model()


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
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # User link (for authentication)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='doctor_profile'
    )

    # Basic info
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

    # Professional
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

    # Profile
    profile_photo = models.ImageField(upload_to='doctors/', blank=True, null=True)
    bio = models.TextField(blank=True, default='', help_text="Short professional biography")
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Doctor'
        verbose_name_plural = 'Doctors'

    def __str__(self):
        # Get the display name: use full_name if available and not 'Unknown', else user's full name, else fallback
        if self.full_name and self.full_name != 'Unknown':
            name = self.full_name
        elif self.user and self.user.get_full_name():
            name = self.user.get_full_name()
        else:
            name = 'Doctor'
        return f"Dr. {name} ({self.registration_number})"

    def save(self, *args, **kwargs):
        if not self.doctor_id:
            self.doctor_id = f"DOC-{random.randint(10000, 99999)}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('doctors:detail', kwargs={'pk': self.pk})