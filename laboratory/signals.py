# laboratory/signals.py
"""
Signal handlers for the Laboratory module.

Handles:
- Logging status changes of LabOrder.
- Automatically updating LabResult timestamps.
- Placeholder for future notification integration.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import LabOrder, LabResult

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------- LabOrder Signals ----------
@receiver(post_save, sender=LabOrder)
def log_lab_order_status_change(sender, instance, created, **kwargs):
    """
    Log when a lab order is created or its status changes.
    """
    if created:
        logger.info(
            f"Lab order {instance.order_number} created for patient {instance.patient} "
            f"by Dr. {instance.doctor} at {instance.hospital}"
        )
    else:
        # Check if status changed (requires fetching old instance)
        # We cannot access old instance directly in post_save; we can either use a pre_save
        # to track changes, or we can use a different approach.
        # For simplicity, we'll log every update.
        logger.info(
            f"Lab order {instance.order_number} updated. Status: {instance.get_status_display()}"
        )


@receiver(pre_save, sender=LabOrder)
def track_order_status_change(sender, instance, **kwargs):
    """
    Log status changes before save (for more accurate logging).
    """
    if instance.pk:
        try:
            old = LabOrder.objects.get(pk=instance.pk)
            if old.status != instance.status:
                logger.info(
                    f"Lab order {instance.order_number} status changed from "
                    f"{old.get_status_display()} to {instance.get_status_display()}"
                )
        except LabOrder.DoesNotExist:
            pass


# ---------- LabResult Signals ----------
@receiver(post_save, sender=LabResult)
def log_result_upload(sender, instance, created, **kwargs):
    """
    Log when a result is uploaded or updated.
    """
    if created:
        logger.info(
            f"Result uploaded for {instance.order_item.test.name} "
            f"(Order: {instance.order_item.lab_order.order_number})"
        )
    else:
        # If verified_by changed, log verification
        # Again, we can use pre_save to track, but we can check if verified_by is now set.
        # Since we don't have old instance, we'll use a simpler approach: log every update.
        logger.info(
            f"Result updated for {instance.order_item.test.name} "
            f"(Order: {instance.order_item.lab_order.order_number})"
        )


@receiver(pre_save, sender=LabResult)
def set_verified_timestamp(sender, instance, **kwargs):
    """
    Automatically set verified_at when verified_by is assigned.
    """
    if instance.pk:
        try:
            old = LabResult.objects.get(pk=instance.pk)
            if old.verified_by is None and instance.verified_by is not None:
                # Verified_by is being set now
                instance.verified_at = timezone.now()
        except LabResult.DoesNotExist:
            pass