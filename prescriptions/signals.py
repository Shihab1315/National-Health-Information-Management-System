# prescriptions/signals.py
"""
Signal handlers for the Prescription module.

Handles:
- Sending notifications when a prescription is created or issued.
- Updating appointment or related records when a prescription changes.
- Logging prescription status changes.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

from .models import Prescription

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------- Placeholder Notification Functions ----------
# In a real implementation, these would send emails, SMS, or in‑app notifications.
def send_notification_to_doctor(prescription):
    """Send notification to the doctor about the prescription."""
    # Example: print or log
    logger.info(f"Notification to Doctor {prescription.doctor}: Prescription {prescription.prescription_number} created for {prescription.patient}.")
    # In production, you would use a notification service.
    # e.g.: Notification.objects.create(user=prescription.doctor.user, message=...)


def send_notification_to_patient(prescription):
    """Send notification to the patient about the prescription."""
    logger.info(f"Notification to Patient {prescription.patient}: Prescription {prescription.prescription_number} issued by Dr. {prescription.doctor}.")
    # e.g.: send_sms(prescription.patient.phone, message)


def send_notification_to_pharmacy(prescription):
    """Send notification to the pharmacy (if any)."""
    # Notify pharmacy to prepare medicines (if integrated)
    logger.info(f"Notification to Pharmacy: Prescription {prescription.prescription_number} issued.")


# ---------- Signal Handlers ----------

@receiver(post_save, sender=Prescription)
def handle_prescription_creation(sender, instance, created, **kwargs):
    """
    When a new prescription is created, send notifications.
    """
    if created:
        # Use transaction.on_commit to ensure notification is sent after the transaction is committed.
        def notify():
            send_notification_to_doctor(instance)
            send_notification_to_patient(instance)
            # Optionally notify pharmacy if status is ISSUED? But we'll handle status change separately.
        transaction.on_commit(notify)


@receiver(post_save, sender=Prescription)
def handle_prescription_status_change(sender, instance, **kwargs):
    """
    When a prescription status changes (e.g., from Draft to Issued), send appropriate notifications.
    """
    # Check if the instance is being updated (not created) and status has changed.
    if instance.pk:
        try:
            old_instance = Prescription.objects.get(pk=instance.pk)
        except Prescription.DoesNotExist:
            return  # Should not happen

        # If status changed to Issued
        if old_instance.status != instance.status and instance.status == Prescription.Status.ISSUED:
            def notify_issued():
                send_notification_to_patient(instance)
                send_notification_to_pharmacy(instance)
            transaction.on_commit(notify_issued)

        # If status changed to Cancelled
        if old_instance.status != instance.status and instance.status == Prescription.Status.CANCELLED:
            def notify_cancelled():
                send_notification_to_patient(instance)
                logger.info(f"Prescription {instance.prescription_number} cancelled.")
            transaction.on_commit(notify_cancelled)


@receiver(pre_delete, sender=Prescription)
def handle_prescription_soft_delete(sender, instance, **kwargs):
    """
    Before soft‑deleting a prescription, log the event.
    This is called when instance.delete() is invoked (which sets deleted_at).
    """
    # The model's delete() method sets deleted_at and saves, so we can log before.
    # We can also prevent deletion if status is Issued (but that's handled in service).
    logger.info(f"Prescription {instance.prescription_number} (ID: {instance.pk}) is being soft‑deleted.")