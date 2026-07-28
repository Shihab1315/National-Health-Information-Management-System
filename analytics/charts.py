from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from patients.models import Patient
from prescriptions.models import Prescription
from laboratory.models import LabOrder, LabResult
from pharmacy.models import Medicine
from doctors.models import Doctor
from hospitals.models import Hospital
from medical_records.models import MedicalRecord
from django.db import models

def get_appointments_per_month(months_back=6):
    """
    Returns data for appointments per month chart.
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=30 * months_back)
    qs = Appointment.objects.filter(
        appointment_date__gte=start_date
    ).annotate(
        month=TruncMonth('appointment_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    labels = [item['month'].strftime('%b %Y') for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_appointments_per_week(weeks_back=12):
    """
    Returns data for appointments per week chart.
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=7 * weeks_back)
    qs = Appointment.objects.filter(
        appointment_date__gte=start_date
    ).annotate(
        week=TruncWeek('appointment_date')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')
    labels = [item['week'].strftime('W%W %b %d') for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_patient_registration_trend(months_back=6):
    """
    Returns patient registration trend over time.
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=30 * months_back)
    qs = Patient.objects.filter(
        created_at__date__gte=start_date
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    labels = [item['month'].strftime('%b %Y') for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_prescription_trend(months_back=6):
    """
    Returns prescription trend over time.
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=30 * months_back)
    qs = Prescription.objects.filter(
        created_at__date__gte=start_date,
        is_deleted=False
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    labels = [item['month'].strftime('%b %Y') for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_lab_trend(months_back=6):
    """
    Returns laboratory order trend over time.
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=30 * months_back)
    qs = LabOrder.objects.filter(
        created_at__date__gte=start_date
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    labels = [item['month'].strftime('%b %Y') for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_medicine_stock_distribution():
    """
    Returns counts of medicines by stock status.
    """
    today = timezone.now().date()
    total = Medicine.objects.filter(is_active=True).count()
    low_stock = Medicine.objects.filter(
        current_stock__lte=models.F('minimum_stock'),
        is_active=True
    ).count()
    out_of_stock = Medicine.objects.filter(
        current_stock=0,
        is_active=True
    ).count()
    expired = Medicine.objects.filter(
        expiry_date__lt=today,
        is_active=True
    ).count()
    available = total - low_stock - out_of_stock
    return {
        'labels': ['Available', 'Low Stock', 'Out of Stock', 'Expired'],
        'data': [available, low_stock, out_of_stock, expired],
    }

def get_appointment_status_pie():
    """
    Returns appointment status distribution.
    """
    qs = Appointment.objects.values('status').annotate(
        count=Count('id')
    )
    labels = [item['status'].capitalize() for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_gender_distribution():
    """
    Returns patient gender distribution.
    """
    qs = Patient.objects.values('gender').annotate(
        count=Count('id')
    )
    # Map gender codes to readable labels
    gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
    labels = [gender_map.get(item['gender'], 'Unknown') for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_hospital_wise_patients():
    """
    Returns number of patients per hospital (based on medical records).
    """
    from medical_records.models import MedicalRecord
    qs = MedicalRecord.objects.filter(
        hospital__isnull=False,
        is_deleted=False
    ).values('hospital__name').annotate(
        count=Count('patient', distinct=True)
    ).order_by('-count')[:10]
    labels = [item['hospital__name'] for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}

def get_doctor_wise_appointments():
    """
    Returns number of appointments per doctor (top 10).
    """
    qs = Appointment.objects.filter(
        doctor__isnull=False
    ).values('doctor__full_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    labels = [f"Dr. {item['doctor__full_name']}" for item in qs]
    data = [item['count'] for item in qs]
    return {'labels': labels, 'data': data}