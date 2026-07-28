from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        HOSPITAL_ADMIN = 'hospital_admin', 'Hospital Admin'
        DOCTOR = 'doctor', 'Doctor'
        RECEPTIONIST = 'receptionist', 'Receptionist'
        LAB_TECHNICIAN = 'lab_technician', 'Lab Technician'
        PHARMACIST = 'pharmacist', 'Pharmacist'
        PATIENT = 'patient', 'Patient'

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.PATIENT,
        help_text="User role – determines permissions and dashboard view"
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    nid = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # Helper methods for permission checks
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    def is_hospital_admin(self):
        return self.role == self.Role.HOSPITAL_ADMIN

    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    def is_receptionist(self):
        return self.role == self.Role.RECEPTIONIST

    def is_lab_technician(self):
        return self.role == self.Role.LAB_TECHNICIAN

    def is_pharmacist(self):
        return self.role == self.Role.PHARMACIST

    def is_patient(self):
        return self.role == self.Role.PATIENT

    def has_role(self, roles):
        """Check if user has any of the given roles (list or single string)."""
        if isinstance(roles, str):
            return self.role == roles
        return self.role in roles