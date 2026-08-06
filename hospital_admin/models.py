# hospital_admin/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from hospitals.models import Hospital, HospitalApplication

User = get_user_model()


class HospitalAdminProfile(models.Model):
    """
    Hospital Admin Profile linked to User.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='hospital_admin_profile'
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='hospital_admins',
        null=True,
        blank=True
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_photo = models.ImageField(
        upload_to='hospital_admins/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hospital Admin Profile'
        verbose_name_plural = 'Hospital Admin Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name or self.user.username

    def get_full_name(self):
        return self.full_name or self.user.get_full_name() or self.user.username


# =============================================================================
# ✅ SIGNALS: Auto-create HospitalAdminProfile
# =============================================================================

@receiver(post_save, sender=User)
def create_hospital_admin_profile(sender, instance, created, **kwargs):
    """
    যখন নতুন User তৈরি হয় এবং role='hospital_admin' হয়,
    তখন HospitalAdminProfile তৈরি করুন।
    """
    if created and instance.role == 'hospital_admin':
        HospitalAdminProfile.objects.get_or_create(
            user=instance,
            defaults={
                'full_name': instance.get_full_name() or instance.username,
                'phone': instance.phone or '',
                'is_active': True
            }
        )
        print(f"✅ HospitalAdminProfile created for {instance.username}")


