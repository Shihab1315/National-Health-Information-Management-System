from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
import random

User = get_user_model()


class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]
    MARITAL_STATUS = [
        ('S', 'Single'),
        ('M', 'Married'),
        ('D', 'Divorced'),
        ('W', 'Widowed'),
    ]

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_profile')
    national_id = models.CharField(max_length=20, unique=True, default='0000000000', verbose_name='National ID / NID')
    health_id = models.CharField(max_length=20, unique=True, blank=True, help_text='Auto-generated NHIMS Health ID')
    full_name = models.CharField(max_length=150, default='Unknown')
    date_of_birth = models.DateField(default='2000-01-01')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    marital_status = models.CharField(max_length=1, choices=MARITAL_STATUS, blank=True, null=True)

    phone = models.CharField(max_length=15, default='0000000000')
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(default='Unknown')
    city = models.CharField(max_length=100, default='')
    district = models.CharField(max_length=100, default='')
    zip_code = models.CharField(max_length=10, blank=True, default='')

    allergies = models.TextField(blank=True, default='', help_text='List known allergies')
    chronic_diseases = models.TextField(blank=True, default='', help_text='List chronic conditions')
    emergency_contact_name = models.CharField(max_length=100, blank=True, default='')
    emergency_contact_phone = models.CharField(max_length=15, blank=True, default='')

    emergency_relationship = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='e.g., Spouse, Parent, Sibling'
    )
    emergency_alt_phone = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text='Alternative phone number for the primary contact'
    )
    emergency_email = models.EmailField(
        blank=True,
        null=True,
        help_text='Email address of the primary contact'
    )
    emergency_address = models.TextField(
        blank=True,
        default='',
        help_text='Address of the primary contact'
    )

    secondary_contact_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Name of the secondary emergency contact'
    )
    secondary_contact_relationship = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='Relationship of the secondary contact'
    )
    secondary_contact_phone = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text='Phone number of the secondary contact'
    )
    secondary_contact_email = models.EmailField(
        blank=True,
        null=True,
        help_text='Email address of the secondary contact'
    )

    is_medical_decision_maker = models.BooleanField(
        default=False,
        help_text='Check if the primary contact is authorized to make emergency medical decisions'
    )

    preferred_ambulance = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Preferred ambulance service provider'
    )

    # ---------- PERMANENT MEDICAL INFORMATION ----------
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Height in centimeters'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Weight in kilograms'
    )
    bmi = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Auto-calculated BMI'
    )

    SMOKING_CHOICES = [
        ('never', 'Never'),
        ('former', 'Former'),
        ('current', 'Current'),
    ]
    smoking_status = models.CharField(
        max_length=10,
        choices=SMOKING_CHOICES,
        blank=True,
        default='',
        help_text='Smoking status'
    )

    ALCOHOL_CHOICES = [
        ('never', 'Never'),
        ('occasionally', 'Occasionally'),
        ('regularly', 'Regularly'),
    ]
    alcohol_consumption = models.CharField(
        max_length=15,
        choices=ALCOHOL_CHOICES,
        blank=True,
        default='',
        help_text='Alcohol consumption'
    )

    EXERCISE_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('light', 'Light'),
        ('moderate', 'Moderate'),
        ('heavy', 'Heavy'),
    ]
    exercise_frequency = models.CharField(
        max_length=10,
        choices=EXERCISE_CHOICES,
        blank=True,
        default='',
        help_text='Exercise frequency'
    )

    DIET_CHOICES = [
        ('non_veg', 'Non-vegetarian'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten-free'),
        ('other', 'Other'),
    ]
    diet_preference = models.CharField(
        max_length=15,
        choices=DIET_CHOICES,
        blank=True,
        default='',
        help_text='Diet preference'
    )

    # ---------- INSURANCE INFORMATION ----------
    has_insurance = models.BooleanField(
        default=False,
        help_text='Does the patient have health insurance?'
    )
    insurance_provider = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Name of the insurance provider'
    )
    insurance_plan = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Name of the insurance plan'
    )
    policy_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='Insurance policy number'
    )
    member_id = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='Member ID / ID card number'
    )
    INSURANCE_TYPE_CHOICES = [
        ('government', 'Government'),
        ('private', 'Private'),
        ('corporate', 'Corporate'),
        ('student', 'Student'),
        ('other', 'Other'),
    ]
    insurance_type = models.CharField(
        max_length=15,
        choices=INSURANCE_TYPE_CHOICES,
        blank=True,
        default='',
        help_text='Type of insurance'
    )
    coverage_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Total coverage amount in BDT'
    )
    coverage_start_date = models.DateField(
        blank=True,
        null=True,
        help_text='Start date of the insurance coverage'
    )
    coverage_end_date = models.DateField(
        blank=True,
        null=True,
        help_text='End date of the insurance coverage'
    )
    coverage_percentage = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Coverage percentage (0-100)'
    )
    emergency_coverage_available = models.BooleanField(
        default=False,
        help_text='Does the policy include emergency coverage?'
    )
    cashless_facility = models.BooleanField(
        default=False,
        help_text='Does the policy offer cashless facility?'
    )
    insurance_notes = models.TextField(
        blank=True,
        default='',
        help_text='Additional notes about the insurance'
    )

    profile_photo = models.ImageField(upload_to='patients/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'

    def __str__(self):
        return f"{self.full_name} ({self.health_id})"

    def save(self, *args, **kwargs):
        if not self.health_id:
            self.health_id = f"NH-{random.randint(100000, 999999)}"
        # Auto-calculate BMI
        if self.height and self.weight and self.height > 0:
            height_m = self.height / 100
            self.bmi = round(self.weight / (height_m * height_m), 2)
        else:
            self.bmi = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('patients:detail', kwargs={'pk': self.pk})