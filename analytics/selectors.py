"""
Selectors are responsible for retrieving data from the database.
They return plain Python objects (lists, dicts) or QuerySets.
All queries are read‑only – no writes happen here.
"""

from django.db.models import Count, Q, Sum, Avg, F
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Any, Optional

# Import models from existing apps (read‑only)
from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital
from appointments.models import Appointment
from prescriptions.models import Prescription
from laboratory.models import LabOrder, LabResult
from pharmacy.models import Medicine
from medical_records.models import MedicalRecord


# -------------------- Patient Selectors --------------------
def get_patients_by_district() -> List[Dict[str, Any]]:
    """Return patient count per district."""
    return list(
        Patient.objects
        .values('district')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

def get_patients_registered_since(days: int = 30) -> int:
    """Return number of patients registered in the last N days."""
    cutoff = timezone.now() - timedelta(days=days)
    return Patient.objects.filter(created_at__gte=cutoff).count()

def get_patient_gender_distribution() -> List[Dict[str, Any]]:
    """Return count of patients by gender."""
    return list(
        Patient.objects
        .values('gender')
        .annotate(count=Count('id'))
        .order_by('gender')
    )

# -------------------- Doctor Selectors --------------------
def get_doctors_by_specialty() -> List[Dict[str, Any]]:
    """Return doctor count per specialty."""
    return list(
        Doctor.objects
        .values('specialties__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

def get_active_doctors_count() -> int:
    """Return number of active doctors."""
    return Doctor.objects.filter(is_active=True).count()

def get_inactive_doctors_count() -> int:
    """Return number of inactive doctors."""
    return Doctor.objects.filter(is_active=False).count()

# -------------------- Hospital Selectors --------------------
def get_hospitals_by_district() -> List[Dict[str, Any]]:
    """Return hospital count per district."""
    return list(
        Hospital.objects
        .values('district')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

def get_total_hospitals() -> int:
    """Return total number of hospitals (active)."""
    return Hospital.objects.filter(is_deleted=False).count()

# -------------------- Appointment Selectors --------------------
def get_appointment_status_counts() -> List[Dict[str, Any]]:
    """Return count of appointments by status."""
    return list(
        Appointment.objects
        .values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )

def get_appointments_today() -> int:
    """Return number of appointments scheduled for today."""
    today = timezone.now().date()
    return Appointment.objects.filter(appointment_date=today).count()

def get_appointments_by_doctor() -> List[Dict[str, Any]]:
    """Return appointment count per doctor (top 5)."""
    return list(
        Appointment.objects
        .values('doctor__full_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

def get_appointments_per_month(months: int = 6) -> List[Dict[str, Any]]:
    """Return count of appointments per month for the last N months."""
    from django.db.models.functions import TruncMonth
    cutoff = timezone.now() - timedelta(days=30 * months)
    return list(
        Appointment.objects
        .filter(appointment_date__gte=cutoff)
        .annotate(month=TruncMonth('appointment_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

# -------------------- Prescription Selectors --------------------
def get_total_prescriptions() -> int:
    """Return total number of prescriptions (not deleted)."""
    return Prescription.objects.filter(is_deleted=False).count()

def get_prescriptions_per_month(months: int = 6) -> List[Dict[str, Any]]:
    """Return count of prescriptions per month for the last N months."""
    from django.db.models.functions import TruncMonth
    cutoff = timezone.now() - timedelta(days=30 * months)
    return list(
        Prescription.objects
        .filter(created_at__gte=cutoff, is_deleted=False)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

# -------------------- Laboratory Selectors --------------------
def get_lab_orders_count_by_status() -> List[Dict[str, Any]]:
    """Return count of lab orders by status."""
    return list(
        LabOrder.objects
        .values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )

def get_lab_orders_per_month(months: int = 6) -> List[Dict[str, Any]]:
    """Return count of lab orders per month for the last N months."""
    from django.db.models.functions import TruncMonth
    cutoff = timezone.now() - timedelta(days=30 * months)
    return list(
        LabOrder.objects
        .filter(created_at__gte=cutoff)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

def get_completed_lab_reports_count() -> int:
    """Return number of published lab reports."""
    return LabResult.objects.filter(report_status='published').count()

def get_pending_lab_orders_count() -> int:
    """Return number of lab orders with status 'pending' or 'collected'."""
    return LabOrder.objects.filter(status__in=['pending', 'collected']).count()

# -------------------- Medicine Selectors --------------------
def get_medicine_stock_summary() -> Dict[str, int]:
    """Return summary: total, low stock, out of stock, expired."""
    today = timezone.now().date()
    total = Medicine.objects.filter(is_active=True).count()
    low = Medicine.objects.filter(current_stock__lte=F('minimum_stock'), is_active=True).count()
    expired = Medicine.objects.filter(expiry_date__lt=today, is_active=True).count()
    out_of_stock = Medicine.objects.filter(current_stock=0, is_active=True).count()
    return {'total': total, 'low': low, 'expired': expired, 'out_of_stock': out_of_stock}

def get_expired_medicines() -> List[Medicine]:
    """Return list of expired medicines."""
    today = timezone.now().date()
    return list(
        Medicine.objects
        .filter(expiry_date__lt=today, is_active=True)
        .order_by('expiry_date')
    )

def get_low_stock_medicines() -> List[Medicine]:
    """Return list of low stock medicines."""
    return list(
        Medicine.objects
        .filter(current_stock__lte=F('minimum_stock'), is_active=True)
        .order_by('current_stock')
    )

# -------------------- Medical Records Selectors --------------------
def get_medical_records_count() -> int:
    """Return total number of medical records (not deleted)."""
    return MedicalRecord.objects.filter(is_deleted=False).count()

def get_recent_medical_records(limit: int = 5) -> List[MedicalRecord]:
    """Return recent medical records."""
    return list(MedicalRecord.objects.filter(is_deleted=False).order_by('-visit_date')[:limit])

# -------------------- Generic Search Selector --------------------
def global_search(query: str) -> Dict[str, List]:
    """
    Perform a global search across multiple models.
    Returns a dictionary with keys: patients, doctors, appointments, etc.
    """
    results = {}
    if query:
        results['patients'] = Patient.objects.filter(
            Q(full_name__icontains=query) |
            Q(health_id__icontains=query) |
            Q(national_id__icontains=query)
        )[:10]
        results['doctors'] = Doctor.objects.filter(
            Q(full_name__icontains=query) |
            Q(registration_number__icontains=query)
        )[:10]
        results['appointments'] = Appointment.objects.filter(
            Q(patient__full_name__icontains=query) |
            Q(doctor__full_name__icontains=query)
        )[:10]
        results['prescriptions'] = Prescription.objects.filter(
            Q(prescription_number__icontains=query) |
            Q(patient__full_name__icontains=query)
        )[:10]
        results['medical_records'] = MedicalRecord.objects.filter(
            Q(patient__full_name__icontains=query) |
            Q(diagnosis__icontains=query)
        )[:10]
        results['medicines'] = Medicine.objects.filter(
            Q(brand_name__icontains=query) |
            Q(generic_name__icontains=query)
        )[:10]
    else:
        results = {key: [] for key in ['patients', 'doctors', 'appointments', 'prescriptions', 'medical_records', 'medicines']}
    return results