from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Notification

User = get_user_model()


def create_notification(recipient, sender, title, message, notification_type,
                        icon='', color='', url='', priority='low'):
    """Helper to create a notification."""
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        notification_type=notification_type,
        icon=icon,
        color=color,
        url=url,
        priority=priority
    )


# -------- Patient Signals --------
@receiver(post_save, sender='patients.Patient')
def patient_created(sender, instance, created, **kwargs):
    if created:
        # Notify admins and the patient themselves
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            create_notification(
                recipient=admin,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title=f"New Patient Registered: {instance.full_name}",
                message=f"A new patient '{instance.full_name}' has been registered.",
                notification_type=Notification.NotificationType.PATIENT_REGISTERED,
                icon='fas fa-user-plus',
                color='text-blue-400',
                url=reverse('patients:detail', args=[instance.id]),
                priority='medium'
            )
        # Optionally notify the patient themselves (if they have a user account)
        if instance.user:
            create_notification(
                recipient=instance.user,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title="Welcome to NHIMS!",
                message="Your patient profile has been created successfully.",
                notification_type=Notification.NotificationType.ACCOUNT_NOTIFICATION,
                icon='fas fa-user-check',
                color='text-green-400',
                url=reverse('patients:detail', args=[instance.id]),
                priority='low'
            )


# -------- Doctor Signals --------
@receiver(post_save, sender='doctors.Doctor')
def doctor_created(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            create_notification(
                recipient=admin,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title=f"New Doctor Added: Dr. {instance.full_name}",
                message=f"Dr. {instance.full_name} has been added to the system.",
                notification_type=Notification.NotificationType.DOCTOR_ADDED,
                icon='fas fa-user-md',
                color='text-cyan-400',
                url=reverse('doctors:detail', args=[instance.id]),
                priority='medium'
            )


# -------- Hospital Signals --------
@receiver(post_save, sender='hospitals.Hospital')
def hospital_created(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            create_notification(
                recipient=admin,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title=f"New Hospital Registered: {instance.name}",
                message=f"Hospital '{instance.name}' has been added.",
                notification_type=Notification.NotificationType.HOSPITAL_ADDED,
                icon='fas fa-hospital',
                color='text-amber-400',
                url=reverse('hospitals:detail', args=[instance.slug]),
                priority='medium'
            )


# -------- Appointment Signals --------
@receiver(post_save, sender='appointments.Appointment')
def appointment_created(sender, instance, created, **kwargs):
    if created:
        # Notify the doctor
        if instance.doctor and instance.doctor.user:
            create_notification(
                recipient=instance.doctor.user,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title="New Appointment Booked",
                message=f"{instance.patient.full_name} booked an appointment with you on {instance.appointment_date}.",
                notification_type=Notification.NotificationType.APPOINTMENT_BOOKED,
                icon='fas fa-calendar-plus',
                color='text-purple-400',
                url=reverse('appointments:detail', args=[instance.id]),
                priority='high'
            )
        # Notify the patient (if they have a user account)
        if instance.patient and instance.patient.user:
            create_notification(
                recipient=instance.patient.user,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title="Appointment Booked",
                message=f"Your appointment with Dr. {instance.doctor.full_name} is scheduled for {instance.appointment_date}.",
                notification_type=Notification.NotificationType.APPOINTMENT_BOOKED,
                icon='fas fa-calendar-check',
                color='text-blue-400',
                url=reverse('appointments:detail', args=[instance.id]),
                priority='high'
            )
        # Notify admins (optional)
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            create_notification(
                recipient=admin,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title=f"Appointment Booked: {instance.patient.full_name}",
                message=f"Appointment with Dr. {instance.doctor.full_name} on {instance.appointment_date}.",
                notification_type=Notification.NotificationType.APPOINTMENT_BOOKED,
                icon='fas fa-calendar-plus',
                color='text-gray-400',
                url=reverse('appointments:detail', args=[instance.id]),
                priority='low'
            )


@receiver(post_save, sender='appointments.Appointment')
def appointment_status_changed(sender, instance, **kwargs):
    # Check if status field exists and if it changed
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            if old.status != instance.status:
                if instance.status == 'confirmed':
                    notif_type = Notification.NotificationType.APPOINTMENT_APPROVED
                    icon = 'fas fa-check-circle'
                    color = 'text-emerald-400'
                    title = "Appointment Confirmed"
                    message = f"Your appointment with Dr. {instance.doctor.full_name} has been confirmed."
                elif instance.status == 'cancelled':
                    notif_type = Notification.NotificationType.APPOINTMENT_CANCELLED
                    icon = 'fas fa-times-circle'
                    color = 'text-red-400'
                    title = "Appointment Cancelled"
                    message = f"Your appointment with Dr. {instance.doctor.full_name} has been cancelled."
                elif instance.status == 'completed':
                    notif_type = Notification.NotificationType.APPOINTMENT_COMPLETED
                    icon = 'fas fa-flag-checkered'
                    color = 'text-emerald-500'
                    title = "Appointment Completed"
                    message = f"Your appointment with Dr. {instance.doctor.full_name} has been marked as completed."
                else:
                    return
                # Notify patient
                if instance.patient and instance.patient.user:
                    create_notification(
                        recipient=instance.patient.user,
                        sender=instance.updated_by if hasattr(instance, 'updated_by') else None,
                        title=title,
                        message=message,
                        notification_type=notif_type,
                        icon=icon,
                        color=color,
                        url=reverse('appointments:detail', args=[instance.id]),
                        priority='high'
                    )
        except sender.DoesNotExist:
            # New object, no status change
            pass


# -------- Prescription Signals --------
@receiver(post_save, sender='prescriptions.Prescription')
def prescription_created(sender, instance, created, **kwargs):
    if created:
        # Notify patient
        if instance.patient and instance.patient.user:
            create_notification(
                recipient=instance.patient.user,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title="New Prescription Generated",
                message=f"A prescription has been created for you by Dr. {instance.doctor.full_name}.",
                notification_type=Notification.NotificationType.PRESCRIPTION_GENERATED,
                icon='fas fa-prescription-bottle',
                color='text-rose-400',
                url=reverse('prescriptions:detail', args=[instance.id]),
                priority='high'
            )
        # Notify pharmacist (if assigned)
        # Notify admins
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            create_notification(
                recipient=admin,
                sender=instance.created_by if hasattr(instance, 'created_by') else None,
                title=f"Prescription Generated: {instance.patient.full_name}",
                message=f"Prescription #{instance.prescription_number} created.",
                notification_type=Notification.NotificationType.PRESCRIPTION_GENERATED,
                icon='fas fa-prescription-bottle',
                color='text-gray-400',
                url=reverse('prescriptions:detail', args=[instance.id]),
                priority='low'
            )


# -------- Laboratory Signals --------
@receiver(post_save, sender='laboratory.LabReport')
def lab_report_created(sender, instance, created, **kwargs):
    if created:
        if instance.order and instance.order.patient and instance.order.patient.user:
            create_notification(
                recipient=instance.order.patient.user,
                sender=instance.verified_by if hasattr(instance, 'verified_by') else None,
                title="Lab Report Ready",
                message=f"Your lab report for order #{instance.order.order_number} is now available.",
                notification_type=Notification.NotificationType.LAB_REPORT_READY,
                icon='fas fa-flask',
                color='text-cyan-400',
                url=reverse('laboratory:report_detail', args=[instance.order.id]),
                priority='high'
            )
        # Also notify the doctor who ordered the test
        if instance.order and instance.order.doctor and instance.order.doctor.user:
            create_notification(
                recipient=instance.order.doctor.user,
                sender=instance.verified_by if hasattr(instance, 'verified_by') else None,
                title=f"Lab Report Ready for {instance.order.patient.full_name}",
                message=f"Lab report for patient {instance.order.patient.full_name} is ready.",
                notification_type=Notification.NotificationType.LAB_REPORT_READY,
                icon='fas fa-flask',
                color='text-blue-400',
                url=reverse('laboratory:report_detail', args=[instance.order.id]),
                priority='medium'
            )


# -------- Pharmacy Signals --------
@receiver(post_save, sender='pharmacy.Sale')
def medicine_dispensed(sender, instance, created, **kwargs):
    if created:
        if instance.patient and instance.patient.user:
            create_notification(
                recipient=instance.patient.user,
                sender=instance.pharmacist if hasattr(instance, 'pharmacist') else None,
                title="Medicine Dispensed",
                message=f"Your medicines for invoice #{instance.invoice_number} have been dispensed.",
                notification_type=Notification.NotificationType.MEDICINE_DISPENSED,
                icon='fas fa-pills',
                color='text-emerald-400',
                url=reverse('pharmacy:invoice', args=[instance.id]),
                priority='medium'
            )