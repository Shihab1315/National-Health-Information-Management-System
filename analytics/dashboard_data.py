from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital
from appointments.models import Appointment
from prescriptions.models import Prescription
from laboratory.models import LabOrder, LabResult
from pharmacy.models import Medicine
from medical_records.models import MedicalRecord
from .constants import CACHE_TIMEOUT, RECENT_LIMIT, CHART_DAYS_BACK

def get_top_stats():
    cache_key = 'analytics_top_stats'
    stats = cache.get(cache_key)
    if stats:
        return stats

    today = timezone.now().date()
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_hospitals = Hospital.objects.filter(is_deleted=False).count()
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    completed_appointments = Appointment.objects.filter(status='completed').count()
    pending_appointments = Appointment.objects.filter(status='pending').count()
    cancelled_appointments = Appointment.objects.filter(status='cancelled').count()
    total_medical_records = MedicalRecord.objects.filter(is_deleted=False).count()
    total_prescriptions = Prescription.objects.filter(is_deleted=False).count()
    total_lab_orders = LabOrder.objects.count()
    completed_lab_reports = LabResult.objects.filter(report_status='published').count()
    total_medicines = Medicine.objects.filter(is_active=True).count()
    low_stock = Medicine.objects.filter(current_stock__lte=F('minimum_stock'), is_active=True).count()
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

def get_recent_activity(limit=RECENT_LIMIT):
    cache_key = 'analytics_recent_activity'
    data = cache.get(cache_key)
    if data:
        return data

    data = {
        'patients': Patient.objects.all().order_by('-created_at')[:limit],
        'appointments': Appointment.objects.all().order_by('-created_at')[:limit],
        'prescriptions': Prescription.objects.filter(is_deleted=False).order_by('-created_at')[:limit],
        'medical_records': MedicalRecord.objects.filter(is_deleted=False).order_by('-visit_date')[:limit],
        'lab_orders': LabOrder.objects.all().order_by('-created_at')[:limit],
    }
    cache.set(cache_key, data, CACHE_TIMEOUT)
    return data

def get_alerts():
    cache_key = 'analytics_alerts'
    alerts = cache.get(cache_key)
    if alerts:
        return alerts

    today = timezone.now().date()
    alert_list = []

    low_stock_items = Medicine.objects.filter(current_stock__lte=F('minimum_stock'), is_active=True).count()
    if low_stock_items:
        alert_list.append({
            'type': 'warning',
            'title': 'Low Stock Medicines',
            'message': f'{low_stock_items} medicines are low in stock.',
            'url': '/pharmacy/inventory/'
        })

    expired_items = Medicine.objects.filter(expiry_date__lt=today, is_active=True).count()
    if expired_items:
        alert_list.append({
            'type': 'danger',
            'title': 'Expired Medicines',
            'message': f'{expired_items} medicines have expired.',
            'url': '/pharmacy/expired/'
        })

    from medical_records.models import FollowUp
    upcoming = FollowUp.objects.filter(
        scheduled_date__date__gte=today,
        scheduled_date__date__lte=today + timedelta(days=3),
        status='scheduled'
    ).count()
    if upcoming:
        alert_list.append({
            'type': 'info',
            'title': 'Upcoming Follow-ups',
            'message': f'{upcoming} follow-ups scheduled in the next 3 days.',
            'url': '/medical-records/'
        })

    pending_lab = LabOrder.objects.filter(status__in=['collected', 'processing']).count()
    if pending_lab:
        alert_list.append({
            'type': 'warning',
            'title': 'Pending Lab Results',
            'message': f'{pending_lab} lab orders are awaiting results.',
            'url': '/laboratory/orders/'
        })

    today_apps = Appointment.objects.filter(appointment_date=today).count()
    if today_apps:
        alert_list.append({
            'type': 'info',
            'title': "Today's Appointments",
            'message': f'{today_apps} appointments scheduled for today.',
            'url': '/appointments/'
        })

    inactive_doctors = Doctor.objects.filter(is_active=False).count()
    if inactive_doctors:
        alert_list.append({
            'type': 'danger',
            'title': 'Inactive Doctors',
            'message': f'{inactive_doctors} doctors are currently inactive.',
            'url': '/doctors/'
        })

    cache.set(cache_key, alert_list, CACHE_TIMEOUT)
    return alert_list

def get_chart_data():
    from django.db.models.functions import TruncMonth
    cache_key = 'analytics_chart_data'
    data = cache.get(cache_key)
    if data:
        return data

    now = timezone.now()
    start_date = now - timedelta(days=CHART_DAYS_BACK)

    appointments_by_month = (
        Appointment.objects
        .filter(appointment_date__gte=start_date)
        .annotate(month=TruncMonth('appointment_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    appt_months = [item['month'].strftime('%b %Y') for item in appointments_by_month]
    appt_counts = [item['count'] for item in appointments_by_month]

    patients_by_month = (
        Patient.objects
        .filter(created_at__gte=start_date)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    patient_months = [item['month'].strftime('%b %Y') for item in patients_by_month]
    patient_counts = [item['count'] for item in patients_by_month]

    prescriptions_by_month = (
        Prescription.objects
        .filter(created_at__gte=start_date, is_deleted=False)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    rx_months = [item['month'].strftime('%b %Y') for item in prescriptions_by_month]
    rx_counts = [item['count'] for item in prescriptions_by_month]

    lab_orders_by_month = (
        LabOrder.objects
        .filter(created_at__gte=start_date)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    lab_months = [item['month'].strftime('%b %Y') for item in lab_orders_by_month]
    lab_counts = [item['count'] for item in lab_orders_by_month]

    status_counts = Appointment.objects.values('status').annotate(count=Count('id'))
    status_labels = [
        dict(getattr(Appointment, 'STATUS_CHOICES', ()) or ()).get(item['status'], item['status'])
        for item in status_counts
    ]
    status_data = [item['count'] for item in status_counts]

    gender_counts = Patient.objects.values('gender').annotate(count=Count('id'))
    gender_labels = [
        dict(getattr(Patient, 'GENDER_CHOICES', ()) or ()).get(item['gender'], item['gender'])
        for item in gender_counts
    ]
    gender_data = [item['count'] for item in gender_counts]

    hospital_patients = (
        Patient.objects
        .values('district')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    hospital_labels = [item['district'] for item in hospital_patients]
    hospital_data = [item['count'] for item in hospital_patients]

    doctor_appts = (
        Appointment.objects
        .values('doctor__full_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    doctor_labels = [item['doctor__full_name'] for item in doctor_appts]
    doctor_data = [item['count'] for item in doctor_appts]

    data = {
        'appointments_per_month': {'labels': appt_months, 'data': appt_counts},
        'patients_per_month': {'labels': patient_months, 'data': patient_counts},
        'prescriptions_per_month': {'labels': rx_months, 'data': rx_counts},
        'lab_orders_per_month': {'labels': lab_months, 'data': lab_counts},
        'appointment_status': {'labels': status_labels, 'data': status_data},
        'gender_distribution': {'labels': gender_labels, 'data': gender_data},
        'hospital_wise_patients': {'labels': hospital_labels, 'data': hospital_data},
        'doctor_wise_appointments': {'labels': doctor_labels, 'data': doctor_data},
    }
    cache.set(cache_key, data, CACHE_TIMEOUT)
    return data