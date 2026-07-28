from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Hospital
import random

@receiver(pre_save, sender=Hospital)
def generate_hospital_code(sender, instance, **kwargs):
    if not instance.hospital_code:
        # Generate a unique code: HOSP-YYYY-XXXX
        year = instance.created_at.year if instance.created_at else 2024
        instance.hospital_code = f"HOSP-{year}-{random.randint(1000, 9999)}"