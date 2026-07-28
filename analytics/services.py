from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta, datetime
from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital
from appointments.models import Appointment
from prescriptions.models import Prescription
from laboratory.models import LabOrder, LabResult
from pharmacy.models import Medicine
from medical_records.models import MedicalRecord, FollowUp
from django.db import models
CACHE_TIMEOUT = 60 * 5  # 5 minutes

def get_dashboard_stats():
    """Get all statistics for the dashboard, cached."""
    cache_key = 'analytics_dashboard_stats'
    stats = cache.get(cache_key)
    if stats:
        return stats

    today = timezone.now().date()
    start_of_today = timezone.make_aware(datetime.combine(today, datetime.min.time()))

    # Patient stats
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_hospitals = Hospital.objects.count()

    # Appointment stats
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    completed_appointments = Appointment.objects.filter(status='completed').count()
    pending_appointments = Appointment.objects.filter(status='pending').count()
    cancelled_appointments = Appointment.objects.filter(status='cancelled').count()

    # Medical records
    total_medical_records = MedicalRecord.objects.filter(is_deleted=False).count()

    # Prescriptions
    total_prescriptions = Prescription.objects.filter(is_deleted=False).count()

    # Lab orders
    total_lab_orders = LabOrder.objects.count()
    completed_lab_reports = LabResult.objects.filter(report_status='published').count()

    # Medicines
    total_medicines = Medicine.objects.filter(is_active=True).count()
    low_stock = Medicine.objects.filter(current_stock__lte=models.F('minimum_stock'), is_active=True).count()
    expired = Medicine.objects.filter(expiry_date__lt=today, is_active=True).count()

    stats = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_hospitals': total_hospitals,
        'total_appointments': total_appointments,
        'today_appointments': today_appointments,
        'completed_appointments': completed_appointments,
        'pending_appointments': pending_appointments,
        'cancelled_appointments': cancelled_appointments,
        'total_medical_records': total_medical_records,
        'total_prescriptions': total_prescriptions,
        'total_lab_orders': total_lab_orders,
        'completed_lab_reports': completed_lab_reports,
        'total_medicines': total_medicines,
        'low_stock': low_stock,
        'expired_medicines': expired,
    }
    cache.set(cache_key, stats, CACHE_TIMEOUT)
    return stats

def get_recent_activity(limit=5):
    """Fetch latest records from various apps."""
    cache_key = 'analytics_recent_activity'
    activity = cache.get(cache_key)
    if activity:
        return activity

    recent_patients = Patient.objects.all().order_by('-created_at')[:limit]
    recent_appointments = Appointment.objects.all().order_by('-created_at')[:limit]
    recent_prescriptions = Prescription.objects.filter(is_deleted=False).order_by('-created_at')[:limit]
    recent_medical_records = MedicalRecord.objects.filter(is_deleted=False).order_by('-visit_date')[:limit]
    recent_lab_orders = LabOrder.objects.all().order_by('-created_at')[:limit]

    activity = {
        'patients': recent_patients,
        'appointments': recent_appointments,
        'prescriptions': recent_prescriptions,
        'medical_records': recent_medical_records,
        'lab_orders': recent_lab_orders,
    }
    cache.set(cache_key, activity, CACHE_TIMEOUT)
    return activity

def get_alerts():
    """Return critical alerts."""
    today = timezone.now().date()
    alerts = []

    # Low stock medicines
    low_stock_items = Medicine.objects.filter(
        current_stock__lte=models.F('minimum_stock'),
        is_active=True
    )[:5]
    if low_stock_items:
        alerts.append({
            'type': 'warning',
            'title': 'Low Stock Medicines',
            'message': f'{low_stock_items.count()} medicines are low in stock.',
            'url': '/pharmacy/inventory/'
        })

    # Expired medicines
    expired_items = Medicine.objects.filter(expiry_date__lt=today, is_active=True)[:5]
    if expired_items:
        alerts.append({
            'type': 'danger',
            'title': 'Expired Medicines',
            'message': f'{expired_items.count()} medicines have expired.',
            'url': '/pharmacy/expired/'
        })

    # Upcoming follow-ups (next 3 days)
    upcoming = FollowUp.objects.filter(
        scheduled_date__date__gte=today,
        scheduled_date__date__lte=today + timedelta(days=3),
        status='scheduled'
    )
    if upcoming:
        alerts.append({
            'type': 'info',
            'title': 'Upcoming Follow-ups',
            'message': f'{upcoming.count()} follow-ups scheduled in the next 3 days.',
            'url': '/medical-records/'
        })

    # Pending lab results (lab orders with status 'collected' or 'processing')
    pending_lab = LabOrder.objects.filter(status__in=['collected', 'processing']).count()
    if pending_lab:
        alerts.append({
            'type': 'warning',
            'title': 'Pending Lab Results',
            'message': f'{pending_lab} lab orders are awaiting results.',
            'url': '/laboratory/orders/'
        })

    # Today's appointments
    today_apps = Appointment.objects.filter(appointment_date=today).count()
    if today_apps:
        alerts.append({
            'type': 'info',
            'title': 'Today\'s Appointments',
            'message': f'{today_apps} appointments scheduled for today.',
            'url': '/appointments/'
        })

    return alerts

def get_chart_data():
    """Prepare data for Chart.js."""
    from django.db.models.functions import TruncMonth, TruncWeek
    now = timezone.now()
    six_months_ago = now - timedelta(days=180)

    # Appointments per month
    appointments_by_month = (
        Appointment.objects
        .filter(appointment_date__gte=six_months_ago)
        .annotate(month=TruncMonth('appointment_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    months = [item['month'].strftime('%b %Y') for item in appointments_by_month] if appointments_by_month else []
    appt_counts = [item['count'] for item in appointments_by_month] if appointments_by_month else []

    # Patient registration trend
    patients_by_month = (
        Patient.objects
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    patient_months = [item['month'].strftime('%b %Y') for item in patients_by_month] if patients_by_month else []
    patient_counts = [item['count'] for item in patients_by_month] if patients_by_month else []

    # Prescription trend
    pres_by_month = (
        Prescription.objects
        .filter(created_at__gte=six_months_ago, is_deleted=False)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    pres_months = [item['month'].strftime('%b %Y') for item in pres_by_month] if pres_by_month else []
    pres_counts = [item['count'] for item in pres_by_month] if pres_by_month else []

    # Appointment status pie chart
    status_counts = Appointment.objects.values('status').annotate(count=Count('id'))
    status_labels = [item['status'] for item in status_counts] if status_counts else []
    status_data = [item['count'] for item in status_counts] if status_counts else []

    return {
        'appointments_per_month': {
            'labels': months,
            'data': appt_counts,
        },
        'patients_per_month': {
            'labels': patient_months,
            'data': patient_counts,
        },
        'prescriptions_per_month': {
            'labels': pres_months,
            'data': pres_counts,
        },
        'appointment_status': {
            'labels': status_labels,
            'data': status_data,
        },
    }