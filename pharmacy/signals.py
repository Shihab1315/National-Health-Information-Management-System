import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction

from .models import Medicine, InventoryLog
from .services import update_stock

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# EXISTING SIGNAL (kept unchanged)
# ----------------------------------------------------------------------
@receiver(post_save, sender=Medicine)
def create_inventory_log_on_creation(sender, instance, created, **kwargs):
    if created and instance.current_stock > 0:
        # initial stock
        InventoryLog.objects.create(
            medicine=instance,
            transaction_type='adjustment',
            quantity=instance.current_stock,
            reference='Initial stock'
        )


# ----------------------------------------------------------------------
# ADDITIVE SIGNALS (new, enterprise-grade)
# ----------------------------------------------------------------------

@receiver(post_save, sender=Medicine)
def notify_low_stock(sender, instance, created, **kwargs):
    """
    Check if medicine is low in stock and log a warning.
    Uses transaction.on_commit to avoid duplicate signals during transactions.
    """
    def _notify():
        try:
            if instance.is_active and instance.current_stock <= instance.minimum_stock:
                if instance.current_stock == 0:
                    level = "CRITICAL"
                else:
                    level = "WARNING"
                logger.warning(
                    f"[{level}] Low stock for {instance.brand_name} "
                    f"(ID: {instance.pk}): {instance.current_stock} left, "
                    f"minimum: {instance.minimum_stock}"
                )
                # Future enhancement: send email notification here
        except Exception as e:
            logger.error(f"Low stock notification failed: {e}", exc_info=True)

    if not created:  # only check updates, not initial creation
        transaction.on_commit(_notify)


@receiver(post_save, sender=Medicine)
def notify_expiry(sender, instance, created, **kwargs):
    """
    Check if medicine is expiring soon or expired and log a warning.
    """
    def _notify():
        try:
            if instance.is_active:
                today = timezone.now().date()
                days_until_expiry = (instance.expiry_date - today).days
                if days_until_expiry < 0:
                    logger.error(
                        f"EXPIRED: {instance.brand_name} (ID: {instance.pk}) "
                        f"expired on {instance.expiry_date}"
                    )
                elif days_until_expiry <= 30:
                    logger.warning(
                        f"Expiring soon: {instance.brand_name} (ID: {instance.pk}) "
                        f"expires in {days_until_expiry} days"
                    )
        except Exception as e:
            logger.error(f"Expiry notification failed: {e}", exc_info=True)

    if not created:
        transaction.on_commit(_notify)


@receiver(post_save, sender=InventoryLog)
def log_inventory_change(sender, instance, created, **kwargs):
    """
    Log every inventory change to the system log for auditing.
    """
    if created:
        def _log():
            try:
                logger.info(
                    f"Inventory change: {instance.medicine.brand_name} "
                    f"type={instance.transaction_type}, qty={instance.quantity}, "
                    f"ref={instance.reference or 'N/A'}, user={instance.created_by}"
                )
            except Exception as e:
                logger.error(f"Inventory log failed: {e}", exc_info=True)
        transaction.on_commit(_log)


# ----------------------------------------------------------------------
# OPTIONAL: Prevent duplicate signals during bulk operations
# (This is an additive guard that can be enabled if needed)
# ----------------------------------------------------------------------
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# 
# class DisableSignals:
#     """Context manager to temporarily disable signals."""
#     def __enter__(self):
#         post_save.disconnect(create_inventory_log_on_creation, sender=Medicine)
#         post_save.disconnect(notify_low_stock, sender=Medicine)
#         post_save.disconnect(notify_expiry, sender=Medicine)
#         post_save.disconnect(log_inventory_change, sender=InventoryLog)
# 
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         post_save.connect(create_inventory_log_on_creation, sender=Medicine)
#         post_save.connect(notify_low_stock, sender=Medicine)
#         post_save.connect(notify_expiry, sender=Medicine)
#         post_save.connect(log_inventory_change, sender=InventoryLog)
# 
# Usage example in management commands:
# with DisableSignals():
#     # bulk operations