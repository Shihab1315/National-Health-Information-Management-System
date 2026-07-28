from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime, date
from decimal import Decimal

from django.apps import apps
from django.db import models, transaction
from django.db.models import (
    Q, Count, Sum, Avg, Min, Max, F, Value, OuterRef, Subquery,
    Case, When, IntegerField, DecimalField
)
from django.db.models.functions import Coalesce, TruncMonth, TruncYear
from django.db.models.query import QuerySet
from django.utils import timezone
from django.core.exceptions import ValidationError

try:
    Vaccination = apps.get_model('vaccinations', 'Vaccination')
except Exception:
    Vaccination = None

from .models import MedicalRecord, Allergy, ChronicDisease, FollowUp
from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital
from prescriptions.models import Prescription
from laboratory.models import LabOrder

import logging

logger = logging.getLogger(__name__)


# ================================
# EXISTING FUNCTIONS (UPGRADED)
# ================================

def get_dashboard_stats() -> Dict[str, Any]:
    """
    Generate statistics for the medical records dashboard.

    Returns:
        dict: A dictionary containing:
            - total_records: Total number of active medical records.
            - today_visits: Records with visit date today.
            - active_patients: Count of distinct patients with active status records.
            - critical_records: Records with systolic BP >= 180.
            - follow_ups_today: Follow-ups scheduled for today.
    """
    today = timezone.now().date()
    
    total_records = MedicalRecord.objects.filter(is_deleted=False).count()
    
    today_visits = MedicalRecord.objects.filter(
        visit_date__date=today,
        is_deleted=False
    ).count()
    
    active_patients = MedicalRecord.objects.filter(
        is_deleted=False,
        status='active'
    ).values('patient').distinct().count()
    
    critical_records = MedicalRecord.objects.filter(
        is_deleted=False,
        blood_pressure_systolic__gte=180
    ).count()
    
    follow_ups_today = FollowUp.objects.filter(
        scheduled_date__date=today,
        status='scheduled'
    ).count()
    
    return {
        'total_records': total_records,
        'today_visits': today_visits,
        'active_patients': active_patients,
        'critical_records': critical_records,
        'follow_ups_today': follow_ups_today,
    }


def get_recent_records(limit: int = 5) -> QuerySet[MedicalRecord]:
    """
    Retrieve the most recent medical records (excluding soft-deleted).

    Args:
        limit: Maximum number of records to return.

    Returns:
        QuerySet of MedicalRecord objects, ordered by visit date descending.
    """
    return MedicalRecord.objects.filter(
        is_deleted=False
    ).select_related(
        'patient', 'doctor'
    ).order_by('-visit_date')[:limit]


def generate_patient_timeline(patient: Patient) -> List[Dict[str, Any]]:
    """
    Generate a chronological timeline of events for a patient.

    Events include:
        - Medical visits
        - Prescriptions
        - Lab orders
        - Vaccinations

    Args:
        patient: Patient instance.

    Returns:
        List of event dictionaries, each containing:
            - type: 'record', 'prescription', 'lab', 'vaccine'
            - date: datetime or date object
            - title: Short description
            - description: Additional details
            - object: The actual model instance (for linking)
    """
    events = []

    # Medical records
    records = MedicalRecord.objects.filter(
        patient=patient,
        is_deleted=False
    ).only(
        'id', 'visit_date', 'diagnosis', 'chief_complaint'
    ).order_by('-visit_date')
    for rec in records:
        events.append({
            'type': 'record',
            'date': rec.visit_date,
            'title': f"Medical Visit - {rec.diagnosis[:50] if rec.diagnosis else 'Visit'}",
            'description': rec.chief_complaint[:100] if rec.chief_complaint else '',
            'object': rec,
        })

    # Prescriptions
    prescriptions = Prescription.objects.filter(
        patient=patient,
        deleted_at__isnull=True
    ).select_related('doctor').only(
        'prescription_number', 'created_at', 'doctor__full_name'
    ).order_by('-created_at')
    for rx in prescriptions:
        events.append({
            'type': 'prescription',
            'date': rx.created_at,
            'title': f"Prescription {rx.prescription_number}",
            'description': f"By Dr. {rx.doctor.full_name}" if rx.doctor else '',
            'object': rx,
        })

    # Lab orders
    lab_orders = LabOrder.objects.filter(
        patient=patient,
        deleted_at__isnull=True
    ).only(
        'order_number', 'created_at', 'status'
    ).order_by('-created_at')
    for lab in lab_orders:
        events.append({
            'type': 'lab',
            'date': lab.created_at,
            'title': f"Lab Order {lab.order_number}",
            'description': f"Status: {lab.get_status_display()}",
            'object': lab,
        })

    # Vaccinations
    if Vaccination is not None:
        vaccines = Vaccination.objects.filter(
            patient=patient
        ).only(
            'administration_date', 'vaccine', 'dose_number'
        ).order_by('-administration_date')
        for v in vaccines:
            vaccine_date = getattr(v, 'administration_date', None)
            if vaccine_date is None:
                continue

            vaccine_label = getattr(v, 'get_vaccine_display', lambda: '')()
            dose_number = getattr(v, 'dose_number', None)

            events.append({
                'type': 'vaccine',
                'date': vaccine_date,
                'title': f"Vaccination - {vaccine_label}",
                'description': f"Dose {dose_number}",
                'object': v,
            })

    # Sort by date descending (most recent first)
    events.sort(key=lambda x: x['date'], reverse=True)
    return events


def get_patient_health_summary(patient: Patient) -> Dict[str, Any]:
    """
    Generate a summary of a patient's health based on their medical records.

    Args:
        patient: Patient instance.

    Returns:
        dict: Contains:
            - total_visits: Number of active records.
            - allergies_count: Total allergies.
            - chronic_count: Active chronic diseases.
            - last_visit: Date of the most recent visit, or None.
            - common_diagnosis: Top 3 most frequent diagnoses.
    """
    records = MedicalRecord.objects.filter(patient=patient, is_deleted=False)
    allergies = Allergy.objects.filter(patient=patient)
    chronic = ChronicDisease.objects.filter(patient=patient, is_active=True)

    last_visit = records.order_by('-visit_date').first()
    common_diagnosis = records.values('diagnosis').annotate(
        count=Count('id')
    ).order_by('-count')[:3]

    return {
        'total_visits': records.count(),
        'allergies_count': allergies.count(),
        'chronic_count': chronic.count(),
        'last_visit': last_visit.visit_date if last_visit else None,
        'common_diagnosis': list(common_diagnosis),
    }


# ================================
# NEW ENTERPRISE HELPER FUNCTIONS
# ================================

def get_patient_statistics(patient: Patient) -> Dict[str, Any]:
    """
    Get comprehensive statistics for a single patient.

    Args:
        patient: Patient instance.

    Returns:
        dict: Patient statistics including record count, vitals averages,
              allergies, chronic conditions, recent activity.
    """
    records = MedicalRecord.objects.filter(patient=patient, is_deleted=False)
    allergies = Allergy.objects.filter(patient=patient)
    chronic = ChronicDisease.objects.filter(patient=patient, is_active=True)

    stats = records.aggregate(
        avg_systolic=Avg('blood_pressure_systolic'),
        avg_diastolic=Avg('blood_pressure_diastolic'),
        avg_pulse=Avg('pulse'),
        avg_temp=Avg('temperature'),
        avg_bmi=Avg('bmi'),
    )

    last_record = records.order_by('-visit_date').first()

    return {
        'total_records': records.count(),
        'allergies_count': allergies.count(),
        'chronic_count': chronic.count(),
        'last_visit': last_record.visit_date if last_record else None,
        'avg_blood_pressure_systolic': stats['avg_systolic'],
        'avg_blood_pressure_diastolic': stats['avg_diastolic'],
        'avg_pulse': stats['avg_pulse'],
        'avg_temperature': stats['avg_temp'],
        'avg_bmi': stats['avg_bmi'],
    }


def get_patient_last_record(patient: Patient) -> Optional[MedicalRecord]:
    """
    Get the most recent medical record for a patient.

    Args:
        patient: Patient instance.

    Returns:
        MedicalRecord instance or None if no records exist.
    """
    return MedicalRecord.objects.filter(
        patient=patient,
        is_deleted=False
    ).select_related('doctor', 'hospital').order_by('-visit_date').first()


def get_patient_latest_prescription(patient: Patient) -> Optional[Prescription]:
    """
    Get the most recent prescription for a patient.

    Args:
        patient: Patient instance.

    Returns:
        Prescription instance or None.
    """
    return Prescription.objects.filter(
        patient=patient,
        deleted_at__isnull=True
    ).select_related('doctor').order_by('-created_at').first()


def get_patient_latest_lab(patient: Patient) -> Optional[LabOrder]:
    """
    Get the most recent lab order for a patient.

    Args:
        patient: Patient instance.

    Returns:
        LabOrder instance or None.
    """
    return LabOrder.objects.filter(
        patient=patient,
        deleted_at__isnull=True
    ).order_by('-created_at').first()


def get_patient_allergies(patient: Patient) -> QuerySet[Allergy]:
    """
    Get all allergies for a patient, ordered by severity.

    Args:
        patient: Patient instance.

    Returns:
        QuerySet of Allergy objects.
    """
    return Allergy.objects.filter(patient=patient).order_by('severity', '-recorded_at')


def get_patient_chronic_diseases(patient: Patient) -> QuerySet[ChronicDisease]:
    """
    Get all active chronic diseases for a patient.

    Args:
        patient: Patient instance.

    Returns:
        QuerySet of ChronicDisease objects where is_active=True.
    """
    return ChronicDisease.objects.filter(
        patient=patient,
        is_active=True
    ).order_by('-diagnosed_date')


def get_patient_followups(patient: Patient, status: Optional[str] = None) -> QuerySet[FollowUp]:
    """
    Get follow-ups for a patient, optionally filtered by status.

    Args:
        patient: Patient instance.
        status: Optional status filter ('scheduled', 'completed', etc.).

    Returns:
        QuerySet of FollowUp objects.
    """
    qs = FollowUp.objects.filter(medical_record__patient=patient)
    if status:
        qs = qs.filter(status=status)
    return qs.select_related('medical_record').order_by('scheduled_date')


def get_recent_followups(limit: int = 5) -> QuerySet[FollowUp]:
    """
    Get the most recent follow-ups across all patients.

    Args:
        limit: Maximum number to return.

    Returns:
        QuerySet of FollowUp objects.
    """
    return FollowUp.objects.filter(
        status='scheduled'
    ).select_related(
        'medical_record', 'medical_record__patient'
    ).order_by('scheduled_date')[:limit]


def get_critical_patients(
    systolic_threshold: int = 180,
    diastolic_threshold: int = 120,
    temp_threshold: float = 103.0,
    limit: int = 10
) -> QuerySet[MedicalRecord]:
    """
    Retrieve patients with critical vitals from their most recent record.

    Args:
        systolic_threshold: Systolic BP threshold.
        diastolic_threshold: Diastolic BP threshold.
        temp_threshold: Temperature threshold (°F).
        limit: Maximum number of records to return.

    Returns:
        QuerySet of MedicalRecord objects with critical vitals.
    """
    return MedicalRecord.objects.filter(
        is_deleted=False
    ).filter(
        Q(blood_pressure_systolic__gte=systolic_threshold) |
        Q(blood_pressure_diastolic__gte=diastolic_threshold) |
        Q(temperature__gte=temp_threshold)
    ).select_related(
        'patient', 'doctor'
    ).order_by(
        '-blood_pressure_systolic',
        '-blood_pressure_diastolic',
        '-temperature'
    )[:limit]


def get_doctor_statistics(doctor: Doctor) -> Dict[str, Any]:
    """
    Get statistics for a specific doctor.

    Args:
        doctor: Doctor instance.

    Returns:
        dict: Total records, recent visits, pending follow-ups, etc.
    """
    records = MedicalRecord.objects.filter(doctor=doctor, is_deleted=False)
    today = timezone.now().date()
    today_visits = records.filter(visit_date__date=today).count()
    total_records = records.count()
    followups = FollowUp.objects.filter(
        medical_record__doctor=doctor,
        status='scheduled'
    ).count()

    return {
        'total_records': total_records,
        'today_visits': today_visits,
        'pending_followups': followups,
        'last_visit': records.order_by('-visit_date').first(),
    }


def get_hospital_statistics(hospital: Hospital) -> Dict[str, Any]:
    """
    Get statistics for a specific hospital.

    Args:
        hospital: Hospital instance.

    Returns:
        dict: Total records, visits today, active patients, etc.
    """
    records = MedicalRecord.objects.filter(hospital=hospital, is_deleted=False)
    today = timezone.now().date()
    today_visits = records.filter(visit_date__date=today).count()
    active_patients = records.filter(status='active').values('patient').distinct().count()

    return {
        'total_records': records.count(),
        'today_visits': today_visits,
        'active_patients': active_patients,
        'critical_records': records.filter(blood_pressure_systolic__gte=180).count(),
    }


def search_medical_records(keyword: str) -> QuerySet[MedicalRecord]:
    """
    Search medical records across multiple fields.

    Args:
        keyword: Search term.

    Returns:
        QuerySet of matching MedicalRecord objects.
    """
    if not keyword:
        return MedicalRecord.objects.none()

    q = Q()
    q |= Q(patient__full_name__icontains=keyword)
    q |= Q(doctor__full_name__icontains=keyword)
    q |= Q(diagnosis__icontains=keyword)
    q |= Q(chief_complaint__icontains=keyword)
    q |= Q(history_of_present_illness__icontains=keyword)

    return MedicalRecord.objects.filter(
        q, is_deleted=False
    ).select_related(
        'patient', 'doctor', 'hospital'
    ).order_by('-visit_date')


def get_monthly_statistics(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Get medical record statistics grouped by month.

    Args:
        year: Optional year to filter; defaults to current year.

    Returns:
        dict: Monthly aggregates (record counts, visits, etc.).
    """
    if year is None:
        year = timezone.now().year

    records = MedicalRecord.objects.filter(
        is_deleted=False,
        visit_date__year=year
    )

    monthly_counts = records.annotate(
        month=TruncMonth('visit_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    return {
        'year': year,
        'monthly_counts': list(monthly_counts),
        'total_records': records.count(),
    }


def get_yearly_statistics(limit: int = 5) -> Dict[str, Any]:
    """
    Get medical record statistics grouped by year.

    Args:
        limit: Number of years to include.

    Returns:
        dict: Yearly aggregates (record counts, visits, etc.).
    """
    qs = MedicalRecord.objects.filter(is_deleted=False)
    yearly_counts = qs.annotate(
        year=TruncYear('visit_date')
    ).values('year').annotate(
        count=Count('id')
    ).order_by('-year')[:limit]

    return {
        'yearly_counts': list(yearly_counts),
    }


def calculate_dashboard_metrics() -> Dict[str, Any]:
    """
    Calculate comprehensive metrics for the dashboard.

    Returns:
        dict: High-level metrics including counts, trends, and alerts.
    """
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)

    # Baseline
    total_records = MedicalRecord.objects.filter(is_deleted=False).count()
    active_records = MedicalRecord.objects.filter(is_deleted=False, status='active').count()
    today_visits = MedicalRecord.objects.filter(visit_date__date=today, is_deleted=False).count()
    week_visits = MedicalRecord.objects.filter(
        visit_date__date__gte=week_ago,
        is_deleted=False
    ).count()

    # Critical alerts
    critical_bp = MedicalRecord.objects.filter(
        is_deleted=False,
        blood_pressure_systolic__gte=180
    ).count()

    followups_today = FollowUp.objects.filter(
        scheduled_date__date=today,
        status='scheduled'
    ).count()

    return {
        'total_records': total_records,
        'active_records': active_records,
        'today_visits': today_visits,
        'week_visits': week_visits,
        'critical_bp_alerts': critical_bp,
        'followups_today': followups_today,
        'trend': 'up' if week_visits > today_visits else 'down',  # simplistic
    }


def build_patient_summary(patient: Patient) -> Dict[str, Any]:
    """
    Build a comprehensive summary for a patient profile.

    Args:
        patient: Patient instance.

    Returns:
        dict: Combined health summary including all relevant data.
    """
    return {
        'statistics': get_patient_statistics(patient),
        'latest_record': get_patient_last_record(patient),
        'latest_prescription': get_patient_latest_prescription(patient),
        'latest_lab': get_patient_latest_lab(patient),
        'allergies': get_patient_allergies(patient),
        'chronic_diseases': get_patient_chronic_diseases(patient),
        'followups': get_patient_followups(patient),
        'summary': get_patient_health_summary(patient),
    }


def build_dashboard_cards() -> Dict[str, Any]:
    """
    Build a set of dashboard summary cards.

    Returns:
        dict: Key metrics ready for rendering.
    """
    today = timezone.now().date()
    stats = get_dashboard_stats()

    return {
        'cards': [
            {
                'title': 'Total Records',
                'value': stats['total_records'],
                'icon': 'fa-file-medical',
                'color': 'blue',
            },
            {
                'title': "Today's Visits",
                'value': stats['today_visits'],
                'icon': 'fa-calendar-day',
                'color': 'green',
            },
            {
                'title': 'Active Patients',
                'value': stats['active_patients'],
                'icon': 'fa-users',
                'color': 'purple',
            },
            {
                'title': 'Critical Cases',
                'value': stats['critical_records'],
                'icon': 'fa-exclamation-triangle',
                'color': 'red',
            },
            {
                'title': "Today's Follow-ups",
                'value': stats['follow_ups_today'],
                'icon': 'fa-clock',
                'color': 'orange',
            },
        ]
    }