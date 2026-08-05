from django.db import models
from django.contrib.auth import get_user_model
from hospitals.models import Hospital

User = get_user_model()

class LabTechnician(models.Model):
    """
    Lab Technician profile model linked to User.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='lab_technician_profile'
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='lab_technicians'
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    profile_photo = models.ImageField(
        upload_to='lab_technicians/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lab Technician'
        verbose_name_plural = 'Lab Technicians'

    def __str__(self):
        return self.full_name or self.user.username

    def get_full_name(self):
        return self.full_name or self.user.get_full_name() or self.user.username