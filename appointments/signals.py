# appointments/signals.py
"""
Signal handlers for the Appointment module.

Handles:
- Sending notifications when an appointment is created.
- Auto‑creating a Medical Record when an appointment is completed.
- Updating appointment status to 'completed' when a prescription is created.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .models import Appointment
from .services import generate_token, generate_appointment_number


# ---------- Placeholder notification functions ----------
# In a real implementation, these would send emails, SMS, or in‑app notifications.
def send_notification_to_doctor(appointment):
    """Send notification to the doctor about a new appointment."""
    # For now, just print or log.
    # Later, integrate with a notification system.
    print(f"Notification to Doctor {appointment.doctor}: New appointment for {appointment.patient} on {appointment.appointment_date} at {appointment.appointment_time}")
    # Implementation would use Django's messages, email, or a notification app.


def send_notification_to_patient(appointment):
    """Send notification to the patient about a new appointment."""
    print(f"Notification to Patient {appointment.patient}: Appointment booked with Dr. {appointment.doctor} on {appointment.appointment_date} at {appointment.appointment_time}")


def send_notification_to_receptionist(appointment):
    """Send notification to receptionist about a new appointment."""
    # Could notify all receptionists or the hospital's reception staff.
    print(f"Notification to Receptionist: New appointment booked for {appointment.patient} with Dr. {appointment.doctor} at {appointment.hospital}")


# ---------- Signal Handlers ----------

@receiver(post_save, sender=Appointment)
def handle_appointment_creation(sender, instance, created, **kwargs):
    """
    When a new appointment is created, send notifications to doctor, patient, and receptionist.
    Also ensure the appointment number and token are set (already done in service).
    """
    if created:
        send_notification_to_doctor(instance)
        send_notification_to_patient(instance)
        send_notification_to_receptionist(instance)


@receiver(post_save, sender=Appointment)
def auto_create_medical_record_on_completion(sender, instance, **kwargs):
    """
    When an appointment status changes to 'completed', automatically create a Medical Record.
    This uses the MedicalRecord model from the medical_records app.
    """
    # Avoid recursion if the signal is triggered multiple times.
    # Check if the status is 'completed' and we haven't already created a record.
    if instance.status == 'completed' and not hasattr(instance, '_medical_record_created'):
        try:
            from medical_records.models import MedicalRecord
            # Check if a record already exists for this appointment to avoid duplicates.
            # Assuming MedicalRecord has a foreign key to Appointment.
            if not MedicalRecord.objects.filter(appointment=instance).exists():
                with transaction.atomic():
                    medical_record = MedicalRecord.objects.create(
                        appointment=instance,
                        patient=instance.patient,
                        doctor=instance.doctor,
                        hospital=instance.hospital,
                        date=timezone.now().date(),
                        # Other fields can be set later via a dedicated form or left empty
                    )
                    # Mark the instance to avoid re-creation if signal fires again.
                    instance._medical_record_created = True
        except ImportError:
            # If medical_records app is not installed, ignore.
            pass
        except Exception as e:
            # Log error but don't break the transaction.
            print(f"Error creating medical record for appointment {instance.pk}: {e}")


# ---------- Signal for Prescription creation (from external app) ----------
# We need to listen to post_save on Prescription model (from prescriptions app).
# This should only work if the prescriptions app is installed.

@receiver(post_save, sender='prescriptions.Prescription')
def update_appointment_status_on_prescription(sender, instance, created, **kwargs):
    """
    When a prescription is created, find the associated appointment and
    mark it as completed (if not already).
    This assumes the Prescription model has a ForeignKey to Appointment.
    """
    if created:
        appointment = instance.appointment  # assuming foreign key
        if appointment and appointment.status != 'completed':
            appointment.status = 'completed'
            appointment.completed_at = timezone.now()
            # Optionally set completed_by = instance.created_by or doctor
            appointment.save(update_fields=['status', 'completed_at'])
            # Optionally trigger medical record creation if not already.
            # The auto_create_medical_record_on_completion signal will handle it.