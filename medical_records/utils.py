import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, List, Union

from django.utils import timezone
from django.db import models
from django.db.models.query import QuerySet
from django.core.exceptions import ValidationError

from .models import MedicalRecord, Allergy, ChronicDisease, Vaccination, FollowUp

logger = logging.getLogger(__name__)


# ================================
# CONSTANTS
# ================================

BMI_CATEGORIES = [
    (0, 18.5, 'Underweight', 'underweight'),
    (18.5, 25.0, 'Normal', 'normal'),
    (25.0, 30.0, 'Overweight', 'overweight'),
    (30.0, 35.0, 'Obese Class I', 'obese_class_i'),
    (35.0, 40.0, 'Obese Class II', 'obese_class_ii'),
    (40.0, float('inf'), 'Obese Class III', 'obese_class_iii'),
]

BLOOD_PRESSURE_CATEGORIES = [
    (None, 120, 80, 'Normal', 'normal'),
    (120, 130, 80, 85, 'Elevated', 'elevated'),
    (130, 140, 85, 90, 'Hypertension Stage 1', 'hypertension_stage1'),
    (140, 180, 90, 120, 'Hypertension Stage 2', 'hypertension_stage2'),
    (180, None, 120, None, 'Hypertensive Crisis', 'hypertensive_crisis'),
]


# ================================
# EXISTING FUNCTIONS (PRESERVED & IMPROVED)
# ================================

def calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> Optional[float]:
    """
    Calculate BMI from height (cm) and weight (kg).

    Args:
        height_cm: Height in centimeters.
        weight_kg: Weight in kilograms.

    Returns:
        BMI value rounded to 2 decimal places, or None if invalid input.
    """
    if not height_cm or not weight_kg:
        return None

    try:
        height_cm = float(height_cm)
        weight_kg = float(weight_kg)
    except (ValueError, TypeError):
        return None

    if height_cm <= 0 or weight_kg <= 0:
        return None

    height_m = height_cm / 100
    if height_m > 0:
        bmi = weight_kg / (height_m ** 2)
        return round(bmi, 2)
    return None


def get_health_summary(patient) -> Dict[str, Any]:
    """
    Return a comprehensive summary of a patient's health metrics.

    Args:
        patient: Patient instance.

    Returns:
        dict: Health summary including visit counts, allergies, chronic diseases,
              vaccines, last visit date, most common diagnosis, and visit counts by year.
    """
    records = MedicalRecord.objects.filter(patient=patient, is_deleted=False)
    allergies = Allergy.objects.filter(patient=patient)
    chronic = ChronicDisease.objects.filter(patient=patient, is_active=True)
    vaccines = Vaccination.objects.filter(patient=patient)

    last_visit = records.order_by('-visit_date').first()

    # Count visits per year
    visit_counts = {}
    for r in records:
        year = r.visit_date.year
        visit_counts[year] = visit_counts.get(year, 0) + 1

    most_common_diagnosis = records.values('diagnosis').annotate(
        count=models.Count('id')
    ).order_by('-count').first()

    return {
        'total_visits': records.count(),
        'allergies_count': allergies.count(),
        'chronic_count': chronic.count(),
        'vaccines_count': vaccines.count(),
        'last_visit_date': last_visit.visit_date if last_visit else None,
        'most_common_diagnosis': most_common_diagnosis,
        'visit_counts_by_year': visit_counts,
    }


def generate_health_id(patient) -> str:
    """
    Generate a unique health ID for a patient.

    Args:
        patient: Patient instance.

    Returns:
        str: Health ID in format HID-{patient.id}-{current_year}.
    """
    # For future use
    return f"HID-{patient.id}-{timezone.now().year}"


def get_upcoming_follow_ups(days: int = 7) -> QuerySet[FollowUp]:
    """
    Retrieve follow-ups scheduled in the next N days.

    Args:
        days: Number of days to look ahead (default: 7).

    Returns:
        QuerySet of FollowUp objects scheduled within the next N days.
    """
    start = timezone.now()
    end = start + timedelta(days=days)
    return FollowUp.objects.filter(
        scheduled_date__range=(start, end),
        status='scheduled'
    ).select_related(
        'medical_record__patient',
        'medical_record__doctor'
    ).order_by('scheduled_date')


# ================================
# NEW HELPER FUNCTIONS (ADDITIVE)
# ================================

def format_blood_pressure(systolic: Optional[int], diastolic: Optional[int]) -> str:
    """
    Format blood pressure as a string.

    Args:
        systolic: Systolic blood pressure.
        diastolic: Diastolic blood pressure.

    Returns:
        str: Formatted BP like "120/80 mmHg" or "N/A" if missing.
    """
    if systolic is None or diastolic is None:
        return "N/A"
    try:
        return f"{int(systolic)}/{int(diastolic)} mmHg"
    except (ValueError, TypeError):
        return "N/A"


def get_bmi_category(bmi: Optional[float]) -> Dict[str, Any]:
    """
    Get BMI category and classification for a given BMI value.

    Args:
        bmi: BMI value.

    Returns:
        dict: Contains 'category' (display name), 'class' (internal key),
              'range' (description of range), and 'color' (visual indicator).
    """
    if bmi is None:
        return {
            'category': 'Unknown',
            'class': 'unknown',
            'range': 'BMI not available',
            'color': 'gray'
        }

    try:
        bmi = float(bmi)
    except (ValueError, TypeError):
        return {
            'category': 'Unknown',
            'class': 'unknown',
            'range': 'Invalid BMI value',
            'color': 'gray'
        }

    for low, high, category, cls in BMI_CATEGORIES:
        if low <= bmi < high:
            return {
                'category': category,
                'class': cls,
                'range': f"{low} - {high}" if high != float('inf') else f"{low}+",
                'color': _get_bmi_color(cls)
            }

    return {
        'category': 'Unknown',
        'class': 'unknown',
        'range': 'N/A',
        'color': 'gray'
    }


def _get_bmi_color(cls: str) -> str:
    """Get color code for BMI category."""
    colors = {
        'underweight': 'orange',
        'normal': 'green',
        'overweight': 'yellow',
        'obese_class_i': 'orange',
        'obese_class_ii': 'red',
        'obese_class_iii': 'darkred',
    }
    return colors.get(cls, 'gray')


def calculate_age(birth_date: Optional[date]) -> Optional[int]:
    """
    Calculate age in years from a birth date.

    Args:
        birth_date: Date of birth.

    Returns:
        int: Age in years, or None if birth_date is invalid.
    """
    if not birth_date:
        return None

    try:
        today = timezone.now().date()
        age = today.year - birth_date.year
        # Subtract if birthday hasn't occurred this year yet
        if today.month < birth_date.month or (
            today.month == birth_date.month and today.day < birth_date.day
        ):
            age -= 1
        return age if age >= 0 else None
    except Exception as e:
        logger.warning(f"Age calculation failed: {e}")
        return None


def calculate_bsa(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    """
    Calculate Body Surface Area using the Mosteller formula.

    Args:
        weight_kg: Weight in kilograms.
        height_cm: Height in centimeters.

    Returns:
        float: BSA in square meters, or None if input invalid.
    """
    if not weight_kg or not height_cm:
        return None

    try:
        weight_kg = float(weight_kg)
        height_cm = float(height_cm)
    except (ValueError, TypeError):
        return None

    if weight_kg <= 0 or height_cm <= 0:
        return None

    height_m = height_cm / 100
    bsa = ((weight_kg * height_m) / 3600) ** 0.5
    return round(bsa, 3)


def validate_vital_signs(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate vital signs against reasonable ranges.

    Args:
        data: Dictionary containing vital sign values.

    Returns:
        dict: Mapping of field names to list of error messages.
    """
    errors = {}

    # Blood pressure
    systolic = data.get('blood_pressure_systolic')
    diastolic = data.get('blood_pressure_diastolic')
    if systolic and (systolic < 60 or systolic > 250):
        errors.setdefault('blood_pressure_systolic', []).append('Systolic BP must be between 60 and 250.')
    if diastolic and (diastolic < 30 or diastolic > 200):
        errors.setdefault('blood_pressure_diastolic', []).append('Diastolic BP must be between 30 and 200.')
    if systolic and diastolic and systolic <= diastolic:
        errors.setdefault('blood_pressure_systolic', []).append('Systolic must be > Diastolic.')

    # Pulse
    pulse = data.get('pulse')
    if pulse and (pulse < 20 or pulse > 250):
        errors.setdefault('pulse', []).append('Pulse must be between 20 and 250 bpm.')

    # Temperature
    temp = data.get('temperature')
    if temp and (temp < 90 or temp > 110):
        errors.setdefault('temperature', []).append('Temperature must be between 90 and 110 °F.')

    # Oxygen saturation
    oxygen = data.get('oxygen_saturation')
    if oxygen and (oxygen < 60 or oxygen > 100):
        errors.setdefault('oxygen_saturation', []).append('Oxygen saturation must be between 60 and 100%.')

    # Respiratory rate
    resp = data.get('respiratory_rate')
    if resp and (resp < 4 or resp > 50):
        errors.setdefault('respiratory_rate', []).append('Respiratory rate must be between 4 and 50 breaths/min.')

    return errors


def calculate_risk_level(patient) -> Dict[str, Any]:
    """
    Calculate a patient's overall risk level based on multiple factors.

    Args:
        patient: Patient instance.

    Returns:
        dict: Contains 'level' (Low, Moderate, High, Critical),
              'score' (numeric), 'factors' (list of contributing factors).
    """
    score = 0
    factors = []

    records = MedicalRecord.objects.filter(patient=patient, is_deleted=False)

    # Check for chronic diseases
    chronic_count = ChronicDisease.objects.filter(patient=patient, is_active=True).count()
    if chronic_count > 0:
        score += 2
        factors.append(f"Active chronic diseases: {chronic_count}")

    # Check for severe allergies
    severe_allergies = Allergy.objects.filter(patient=patient, severity='severe').count()
    if severe_allergies > 0:
        score += 2
        factors.append(f"Severe allergies: {severe_allergies}")

    # Check recent critical vitals
    last_record = records.order_by('-visit_date').first()
    if last_record:
        if last_record.blood_pressure_systolic and last_record.blood_pressure_systolic >= 180:
            score += 3
            factors.append(f"Critical systolic BP: {last_record.blood_pressure_systolic}")
        if last_record.blood_pressure_diastolic and last_record.blood_pressure_diastolic >= 120:
            score += 3
            factors.append(f"Critical diastolic BP: {last_record.blood_pressure_diastolic}")
        if last_record.temperature and last_record.temperature >= 103:
            score += 2
            factors.append(f"High temperature: {last_record.temperature}°F")
        if last_record.pulse and (last_record.pulse > 120 or last_record.pulse < 50):
            score += 2
            factors.append(f"Abnormal pulse: {last_record.pulse} bpm")

    # Determine level
    if score >= 5:
        level = 'Critical'
    elif score >= 3:
        level = 'High'
    elif score >= 1:
        level = 'Moderate'
    else:
        level = 'Low'

    return {
        'level': level,
        'score': score,
        'factors': factors,
    }


def calculate_followup_days(scheduled_date: date) -> int:
    """
    Calculate the number of days until a follow-up.

    Args:
        scheduled_date: Scheduled follow-up date.

    Returns:
        int: Number of days until the scheduled date (negative if past).
    """
    if not scheduled_date:
        return 0
    today = timezone.now().date()
    delta = scheduled_date - today
    return delta.days


def generate_medical_record_number(patient_id: int, visit_date: date) -> str:
    """
    Generate a unique medical record number.

    Format: MR-YYYYMMDD-PXXXXX (P = patient ID prefix)

    Args:
        patient_id: ID of the patient.
        visit_date: Date of the visit.

    Returns:
        str: Unique record number.
    """
    date_part = visit_date.strftime('%Y%m%d')
    return f"MR-{date_part}-P{patient_id:05d}"


def generate_attachment_path(instance, filename: str) -> str:
    """
    Generate a file path for attachments.

    Args:
        instance: Attachment instance.
        filename: Original filename.

    Returns:
        str: Path like 'medical_records/attachments/YYYY/MM/DD/filename'.
    """
    now = timezone.now()
    path_parts = [
        'medical_records',
        'attachments',
        now.strftime('%Y'),
        now.strftime('%m'),
        now.strftime('%d'),
        filename
    ]
    return '/'.join(path_parts)


def safe_decimal(value: Any, default: float = 0.0) -> Decimal:
    """
    Safely convert a value to Decimal.

    Args:
        value: Value to convert.
        default: Default value if conversion fails.

    Returns:
        Decimal: Converted value or default.
    """
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal(str(default))


def safe_percentage(value: float, max_val: float = 100.0) -> float:
    """
    Safely calculate a percentage.

    Args:
        value: Current value.
        max_val: Maximum value.

    Returns:
        float: Percentage (0-100), rounded to 1 decimal place.
    """
    if not value or not max_val:
        return 0.0
    try:
        pct = (value / max_val) * 100
        return round(max(0, min(100, pct)), 1)
    except (ZeroDivisionError, TypeError):
        return 0.0


def format_temperature(temp_f: Optional[float]) -> str:
    """
    Format temperature in Fahrenheit.

    Args:
        temp_f: Temperature in Fahrenheit.

    Returns:
        str: Formatted temperature like "98.6 °F" or "N/A".
    """
    if temp_f is None:
        return "N/A"
    try:
        return f"{float(temp_f):.1f} °F"
    except (ValueError, TypeError):
        return "N/A"


def format_weight(weight_kg: Optional[float]) -> str:
    """
    Format weight in kilograms.

    Args:
        weight_kg: Weight in kilograms.

    Returns:
        str: Formatted weight like "70.5 kg" or "N/A".
    """
    if weight_kg is None:
        return "N/A"
    try:
        return f"{float(weight_kg):.1f} kg"
    except (ValueError, TypeError):
        return "N/A"


def format_height(height_cm: Optional[float]) -> str:
    """
    Format height in centimeters.

    Args:
        height_cm: Height in centimeters.

    Returns:
        str: Formatted height like "175.0 cm" or "N/A".
    """
    if height_cm is None:
        return "N/A"
    try:
        return f"{float(height_cm):.1f} cm"
    except (ValueError, TypeError):
        return "N/A"


def format_datetime(dt: Optional[datetime]) -> str:
    """
    Format a datetime object in a standard format.

    Args:
        dt: Datetime object.

    Returns:
        str: Formatted datetime like "Jan 15, 2024 2:30 PM" or "N/A".
    """
    if not dt:
        return "N/A"
    try:
        return dt.strftime('%b %d, %Y %I:%M %p')
    except Exception:
        return "N/A"


def get_current_age_in_months(birth_date: Optional[date]) -> Optional[int]:
    """
    Calculate age in months from a birth date.

    Args:
        birth_date: Date of birth.

    Returns:
        int: Age in months, or None if invalid.
    """
    if not birth_date:
        return None
    try:
        today = timezone.now().date()
        months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
        if today.day < birth_date.day:
            months -= 1
        return max(0, months)
    except Exception:
        return None


def is_valid_date_range(start_date: date, end_date: date) -> bool:
    """
    Check if a date range is valid (start ≤ end).

    Args:
        start_date: Start date.
        end_date: End date.

    Returns:
        bool: True if start_date <= end_date, False otherwise.
    """
    if not start_date or not end_date:
        return False
    return start_date <= end_date