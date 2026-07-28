import logging
import re
from datetime import date, datetime
from typing import Any, Optional, Union
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# ================================
# CONSTANTS
# ================================

ALLOWED_FILE_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'csv']
ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'bmp']
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx']
ALLOWED_PDF_EXTENSIONS = ['pdf']

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# ================================
# EXISTING VALIDATORS (PRESERVED & IMPROVED)
# ================================

def validate_positive_number(value):
    """
    Ensure the value is greater than zero.

    Args:
        value: Numeric value to validate.

    Raises:
        ValidationError: If value is not positive.
    """
    if value is not None and value <= 0:
        raise ValidationError(_('Value must be greater than zero.'))


def validate_weight(value):
    """
    Validate weight in kilograms (range: 2–500 kg).

    Args:
        value: Weight value.

    Raises:
        ValidationError: If weight is outside allowed range.
    """
    if value is not None and (value < 2 or value > 500):
        raise ValidationError(_('Weight must be between 2 and 500 kg.'))


def validate_height(value):
    """
    Validate height in centimeters (range: 30–300 cm).

    Args:
        value: Height value.

    Raises:
        ValidationError: If height is outside allowed range.
    """
    if value is not None and (value < 30 or value > 300):
        raise ValidationError(_('Height must be between 30 and 300 cm.'))


def validate_blood_pressure_systolic(value):
    """
    Validate systolic blood pressure (range: 40–300 mmHg).

    Args:
        value: Systolic BP value.

    Raises:
        ValidationError: If outside allowed range.
    """
    if value is not None and (value < 40 or value > 300):
        raise ValidationError(_('Systolic BP must be between 40 and 300 mmHg.'))


def validate_blood_pressure_diastolic(value):
    """
    Validate diastolic blood pressure (range: 20–200 mmHg).

    Args:
        value: Diastolic BP value.

    Raises:
        ValidationError: If outside allowed range.
    """
    if value is not None and (value < 20 or value > 200):
        raise ValidationError(_('Diastolic BP must be between 20 and 200 mmHg.'))


def validate_pulse(value):
    """
    Validate pulse rate (range: 20–300 bpm).

    Args:
        value: Pulse rate.

    Raises:
        ValidationError: If pulse is outside allowed range.
    """
    if value is not None and (value < 20 or value > 300):
        raise ValidationError(_('Pulse must be between 20 and 300 bpm.'))


def validate_temperature(value):
    """
    Validate temperature in Fahrenheit (range: 32–110 °F).

    Args:
        value: Temperature value.

    Raises:
        ValidationError: If temperature is outside allowed range.
    """
    if value is not None and (value < 32 or value > 110):
        raise ValidationError(_('Temperature must be between 32 and 110 °F.'))


def validate_oxygen_saturation(value):
    """
    Validate oxygen saturation (range: 50–100%).

    Args:
        value: Oxygen saturation percentage.

    Raises:
        ValidationError: If value is outside allowed range.
    """
    if value is not None and (value < 50 or value > 100):
        raise ValidationError(_('Oxygen saturation must be between 50 and 100%.'))


def validate_file_extension(value):
    """
    Validate file extension against allowed list.

    Args:
        value: File object.

    Raises:
        ValidationError: If file extension is not allowed.
    """
    ext = value.name.split('.')[-1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(
            _(f'Unsupported file type. Allowed: {", ".join(ALLOWED_FILE_EXTENSIONS)}')
        )


def validate_file_size(value):
    """
    Validate file size (max 20 MB).

    Args:
        value: File object.

    Raises:
        ValidationError: If file exceeds maximum size.
    """
    if value.size > MAX_FILE_SIZE:
        raise ValidationError(
            _(f'File size exceeds 20 MB (current: {value.size / 1024 / 1024:.1f} MB).')
        )


# ================================
# NEW VALIDATORS (ADDITIVE)
# ================================

def validate_bmi(bmi: Optional[float]) -> None:
    """
    Validate BMI (range: 5–80).

    Args:
        bmi: BMI value.

    Raises:
        ValidationError: If BMI is outside reasonable range.
    """
    if bmi is not None and (bmi < 5 or bmi > 80):
        raise ValidationError(_('BMI must be between 5 and 80.'))


def validate_respiratory_rate(value: Optional[int]) -> None:
    """
    Validate respiratory rate (range: 4–50 breaths/min).

    Args:
        value: Respiratory rate.

    Raises:
        ValidationError: If rate is outside allowed range.
    """
    if value is not None and (value < 4 or value > 50):
        raise ValidationError(_('Respiratory rate must be between 4 and 50 breaths/min.'))


def validate_followup_date(value):
    """
    Validate follow-up date is not before the associated visit date (if available).

    Note: This validator requires access to the instance; use in form or model clean.
    This is a placeholder – the actual validation should be done with access to the
    parent MedicalRecord. For standalone use, it only checks that the date is not
    in the distant past (you can implement a separate check).

    Args:
        value: Follow-up date.

    Raises:
        ValidationError: If date is more than 10 years in the past (sanity check).
    """
    if value:
        now = timezone.now().date()
        if value < now - timezone.timedelta(days=365 * 10):
            raise ValidationError(_('Follow-up date cannot be more than 10 years in the past.'))


def validate_visit_date(value):
    """
    Validate that the visit date is not in the future.

    Args:
        value: Visit date.

    Raises:
        ValidationError: If date is in the future.
    """
    if value:
        now = timezone.now()
        if isinstance(value, datetime) and value > now:
            raise ValidationError(_('Visit date cannot be in the future.'))
        elif isinstance(value, date) and value > now.date():
            raise ValidationError(_('Visit date cannot be in the future.'))


def validate_future_date(value):
    """
    Validate that a date is in the future (for scheduled events).

    Args:
        value: Date to validate.

    Raises:
        ValidationError: If date is not in the future.
    """
    if value:
        now = timezone.now().date()
        if value <= now:
            raise ValidationError(_('Date must be in the future.'))


def validate_not_future_datetime(value):
    """
    Validate that a datetime is not in the future.

    Args:
        value: DateTime to validate.

    Raises:
        ValidationError: If datetime is in the future.
    """
    if value:
        now = timezone.now()
        if value > now:
            raise ValidationError(_('Date/time cannot be in the future.'))


def validate_medical_notes(value: str) -> None:
    """
    Validate medical notes text (allow empty, but if provided, ensure reasonable length).

    Args:
        value: Medical notes text.

    Raises:
        ValidationError: If text exceeds maximum length.
    """
    if value and len(value) > 5000:
        raise ValidationError(_('Medical notes cannot exceed 5000 characters.'))


def validate_diagnosis(value: str) -> None:
    """
    Validate diagnosis text (ensure not too short/too long).

    Args:
        value: Diagnosis text.

    Raises:
        ValidationError: If length is inappropriate.
    """
    if value:
        if len(value) < 2:
            raise ValidationError(_('Diagnosis must be at least 2 characters.'))
        if len(value) > 1000:
            raise ValidationError(_('Diagnosis cannot exceed 1000 characters.'))


def validate_chief_complaint(value: str) -> None:
    """
    Validate chief complaint text.

    Args:
        value: Chief complaint text.

    Raises:
        ValidationError: If text is too short or too long.
    """
    if value:
        if len(value) < 2:
            raise ValidationError(_('Chief complaint must be at least 2 characters.'))
        if len(value) > 500:
            raise ValidationError(_('Chief complaint cannot exceed 500 characters.'))


def validate_phone_number(value: str) -> None:
    """
    Validate a phone number (BD format).

    Args:
        value: Phone number string.

    Raises:
        ValidationError: If format is invalid.
    """
    if value:
        # Remove any spaces, dashes, parentheses
        cleaned = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^\+?[0-9]{10,15}$', cleaned):
            raise ValidationError(_('Enter a valid phone number (10-15 digits, optional leading +).'))


def validate_email(value: str) -> None:
    """
    Validate email address format.

    Args:
        value: Email string.

    Raises:
        ValidationError: If email format is invalid.
    """
    if value:
        # Basic email regex
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise ValidationError(_('Enter a valid email address.'))


def validate_age(age: Optional[int]) -> None:
    """
    Validate age (range: 0–150).

    Args:
        age: Age in years.

    Raises:
        ValidationError: If age is outside reasonable range.
    """
    if age is not None and (age < 0 or age > 150):
        raise ValidationError(_('Age must be between 0 and 150 years.'))


def validate_dose_number(value: Optional[int]) -> None:
    """
    Validate dose number (must be >= 1).

    Args:
        value: Dose number.

    Raises:
        ValidationError: If dose number is less than 1.
    """
    if value is not None and value < 1:
        raise ValidationError(_('Dose number must be at least 1.'))


def validate_attachment_name(value: str) -> None:
    """
    Validate attachment name (sanitize, ensure length).

    Args:
        value: Attachment name.

    Raises:
        ValidationError: If name is invalid or too long.
    """
    if value:
        if len(value) > 200:
            raise ValidationError(_('Attachment name cannot exceed 200 characters.'))
        # Disallow dangerous characters
        if not re.match(r'^[a-zA-Z0-9\-_\. ]+$', value):
            raise ValidationError(_('Attachment name can only contain letters, numbers, spaces, dots, hyphens, and underscores.'))


def validate_file_name(value: str) -> None:
    """
    Validate a file name (basic safety).

    Args:
        value: File name.

    Raises:
        ValidationError: If name is empty or too long.
    """
    if value:
        if len(value) > 255:
            raise ValidationError(_('File name cannot exceed 255 characters.'))
        if not value.strip():
            raise ValidationError(_('File name cannot be empty.'))


def validate_image_extension(value):
    """
    Validate that file extension is an allowed image type.

    Args:
        value: File object.

    Raises:
        ValidationError: If extension is not an image type.
    """
    ext = value.name.split('.')[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            _(f'Only image files are allowed: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}')
        )


def validate_document_extension(value):
    """
    Validate that file extension is an allowed document type.

    Args:
        value: File object.

    Raises:
        ValidationError: If extension is not a document type.
    """
    ext = value.name.split('.')[-1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            _(f'Only document files are allowed: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}')
        )


def validate_pdf_extension(value):
    """
    Validate that file extension is PDF.

    Args:
        value: File object.

    Raises:
        ValidationError: If extension is not PDF.
    """
    ext = value.name.split('.')[-1].lower()
    if ext not in ALLOWED_PDF_EXTENSIONS:
        raise ValidationError(_('Only PDF files are allowed.'))


def validate_percentage(value: Optional[float]) -> None:
    """
    Validate that a value is a percentage (0–100).

    Args:
        value: Percentage value.

    Raises:
        ValidationError: If value is outside 0–100.
    """
    if value is not None and (value < 0 or value > 100):
        raise ValidationError(_('Value must be between 0 and 100%.'))


def validate_text_length(value: str, min_len: int = 1, max_len: int = 500) -> None:
    """
    Validate that text length is within a specified range.

    Args:
        value: Text string.
        min_len: Minimum length (default 1).
        max_len: Maximum length (default 500).

    Raises:
        ValidationError: If text length is outside the range.
    """
    if value:
        length = len(value)
        if length < min_len:
            raise ValidationError(_(f'Text must be at least {min_len} characters.'))
        if length > max_len:
            raise ValidationError(_(f'Text cannot exceed {max_len} characters.'))