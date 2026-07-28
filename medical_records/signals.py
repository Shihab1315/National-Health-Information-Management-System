import logging
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist

from .models import MedicalRecord, FollowUp
from .utils import calculate_bmi


def get_create_notification():
    """
    Safely resolve the notifications service function when the notifications
    app is installed. Returns None when the dependency is unavailable.
    """
    try:
        from importlib import import_module

        services = import_module("notifications.services")
        return getattr(services, "create_notification", None)
    except ImportError:
        return None


logger = logging.getLogger(__name__)


# ================================
# EXISTING SIGNALS (UPGRADED)
# ================================

@receiver(pre_save, sender=MedicalRecord)
def auto_calculate_bmi(sender, instance, **kwargs):
    """
    Automatically calculate BMI from height and weight before saving.

    This signal runs before saving a MedicalRecord instance. If both height
    and weight are provided, it calculates BMI using the utility function.
    It skips calculation if either field is missing.
    """
    if instance.height and instance.weight:
        try:
            instance.bmi = calculate_bmi(instance.height, instance.weight)
        except Exception as e:
            logger.error(f"BMI calculation failed for MedicalRecord {instance.pk}: {e}")
            # Do not raise; let the save proceed without BMI


@receiver(post_save, sender=MedicalRecord)
def create_follow_up_reminder(sender, instance, created, **kwargs):
    """
    Automatically create a FollowUp entry when a record has a follow_up_date.

    This signal runs after saving a MedicalRecord. If the record has a
    follow_up_date and no existing FollowUp is linked, it creates a new
    FollowUp with status 'scheduled'. The creation is wrapped in
    transaction.on_commit to ensure it happens after the transaction commits.
    """
    if not instance.follow_up_date:
        return

    # Avoid duplicate follow-ups
    if instance.follow_ups.exists():
        return

    def create_followup():
        try:
            FollowUp.objects.create(
                medical_record=instance,
                scheduled_date=instance.follow_up_date,
                status='scheduled',
                notes='Auto-generated from record follow-up date.'
            )
            logger.info(f"Auto-generated follow-up for MedicalRecord {instance.pk}")
        except Exception as e:
            logger.error(f"Failed to create follow-up for MedicalRecord {instance.pk}: {e}")

    transaction.on_commit(create_followup)


# ================================
# NEW SAFE SIGNALS (ADDITIVE)
# ================================

@receiver(post_save, sender=FollowUp)
def notify_followup_reminder(sender, instance, created, **kwargs):
    """
    Trigger a notification when a follow-up is created or updated.

    This signal checks if the Notifications app exists and is installed.
    If so, it creates a notification for the patient and doctor when a
    follow-up is scheduled. It uses a safe resolver to avoid ImportError.
    """
    if not created:
        # Only notify on new follow-ups
        return

    if instance.status != 'scheduled':
        return

    create_notification = get_create_notification()
    if create_notification is None:
        logger.debug("Notifications app not installed, skipping notification creation.")
        return

    try:
        # Create notification for patient
        patient = instance.medical_record.patient
        if patient and patient.user:
            create_notification(
                recipient=patient.user,
                title="Follow-up Scheduled",
                message=f"Your follow-up is scheduled for {instance.scheduled_date}.",
                notification_type='reminder',
                related_object=instance
            )

        # Create notification for doctor (if doctor exists)
        doctor = instance.medical_record.doctor
        if doctor and doctor.user:
            create_notification(
                recipient=doctor.user,
                title="Follow-up Scheduled",
                message=f"Follow-up for {patient.full_name} is scheduled for {instance.scheduled_date}.",
                notification_type='reminder',
                related_object=instance
            )

        logger.info(f"Notifications created for FollowUp {instance.pk}")

    except Exception as e:
        logger.error(f"Failed to create notification for FollowUp {instance.pk}: {e}")


@receiver(post_save, sender=MedicalRecord)
def update_patient_timeline_cache(sender, instance, **kwargs):
    """
    Trigger a cache refresh for the patient timeline.

    This signal is a placeholder for any cache invalidation logic.
    It runs on commit to avoid holding locks.
    """
    # Only run if cache is configured
    try:
        from django.core.cache import cache
        cache_key = f"patient_timeline_{instance.patient_id}"
        transaction.on_commit(lambda: cache.delete(cache_key))
        logger.debug(f"Cache invalidated for patient {instance.patient_id}")
    except ImportError:
        # Cache not configured; ignore
        pass
    except Exception as e:
        logger.error(f"Cache invalidation failed for patient {instance.patient_id}: {e}")


@receiver(post_save, sender=FollowUp)
def update_medical_record_status(sender, instance, **kwargs):
    """
    Automatically update the parent MedicalRecord status when a follow-up is completed.
    """
    if instance.status == 'completed' and not instance.medical_record.is_deleted:
        # Only update if record is not soft-deleted
        medical_record = instance.medical_record
        # Avoid updating if already completed or cancelled
        if medical_record.status not in ['completed', 'cancelled']:
            medical_record.status = 'completed'
            medical_record.save(update_fields=['status'])
            logger.info(f"MedicalRecord {medical_record.pk} status updated to 'completed' via FollowUp {instance.pk}")


@receiver(post_delete, sender=FollowUp)
def log_followup_deletion(sender, instance, **kwargs):
    """
    Log when a follow-up is deleted (soft or hard delete).
    """
    logger.info(f"FollowUp {instance.pk} for MedicalRecord {instance.medical_record_id} was deleted.")


# ================================
# CONDITIONAL IMPORT HANDLING
# ================================
# Ensure that signals using notifications app are safe even if the app is missing.
# The lazy import inside the signal function handles this.