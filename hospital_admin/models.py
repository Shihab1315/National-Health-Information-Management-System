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


@receiver(post_save, sender=HospitalApplication)
def update_hospital_admin_profile(sender, instance, created, **kwargs):
    """
    যখন HospitalApplication approved হয়,
    তখন HospitalAdminProfile-এ hospital যোগ করুন।
    """
    # ✅ শুধুমাত্র approved status-এ কাজ করবে
    if instance.status == 'approved':
        print(f"🔍 Application {instance.application_number} approved!")
        
        # ✅ HospitalApplication থেকে hospital খুঁজুন
        # HospitalApplication মডেলে hospital_id নেই, তাই hospital_admin থেকে hospital বের করুন
        try:
            # হাসপাতাল অ্যাডমিনের সাথে সংযুক্ত হাসপাতাল খুঁজুন
            from hospital_admin.models import HospitalAdminProfile
            profile = HospitalAdminProfile.objects.get(user=instance.hospital_admin)
            
            # যদি প্রোফাইলে hospital থাকে
            if profile.hospital:
                print(f"✅ Hospital found from profile: {profile.hospital}")
                # প্রোফাইল ইতিমধ্যে আপডেট করা আছে
                return
            else:
                print(f"❌ No hospital in profile for {instance.hospital_admin.username}")
                
        except HospitalAdminProfile.DoesNotExist:
            print(f"❌ HospitalAdminProfile not found for {instance.hospital_admin.username}")
            
        # ⚠️ যদি hospital না পাওয়া যায়, তাহলে প্রথম হাসপাতাল নিন (অস্থায়ী সমাধান)
        try:
            hospital = Hospital.objects.first()
            if hospital:
                profile, created = HospitalAdminProfile.objects.get_or_create(
                    user=instance.hospital_admin,
                    defaults={
                        'hospital': hospital,
                        'full_name': instance.hospital_admin.get_full_name() or instance.hospital_admin.username,
                        'phone': instance.hospital_admin.phone or '',
                        'is_active': True
                    }
                )
                if not created:
                    profile.hospital = hospital
                    profile.is_active = True
                    profile.save()
                print(f"✅ HospitalAdminProfile updated with first hospital: {hospital}")
            else:
                print(f"❌ No hospital found in system!")
        except Exception as e:
            print(f"❌ Error: {e}")