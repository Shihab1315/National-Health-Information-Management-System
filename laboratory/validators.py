# laboratory/validators.py
"""
Custom validators for the Laboratory module.

Used across models and forms to enforce data integrity.
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


def validate_test_code(value):
    """
    Validate that the test code contains only uppercase letters, digits, and hyphens.
    """
    if not re.match(r'^[A-Z0-9\-]+$', value):
        raise ValidationError(
            _('Test code must contain only uppercase letters, digits, and hyphens.')
        )


def validate_positive_price(value):
    """
    Ensure price is not negative.
    """
    if value < 0:
        raise ValidationError(
            _('Price cannot be negative.')
        )


def validate_non_negative_integer(value):
    """
    Ensure integer is not negative (for future use).
    """
    if value < 0:
        raise ValidationError(
            _('Value cannot be negative.')
        )


def validate_future_date(value):
    """
    Ensure a date is not in the past (for follow-up dates, collection dates, etc.)
    """
    if value and value < timezone.now().date():
        raise ValidationError(
            _('Date cannot be in the past.')
        )


def validate_past_or_present_date(value):
    """
    Ensure a date is not in the future (for birth dates, etc.)
    """
    if value and value > timezone.now().date():
        raise ValidationError(
            _('Date cannot be in the future.')
        )


def validate_file_extension(value):
    """
    Validate file extension for uploaded reports.
    """
    ext = value.name.split('.')[-1].lower()
    allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
    if ext not in allowed_extensions:
        raise ValidationError(
            _('Only PDF, JPEG, and PNG files are allowed.')
        )


def validate_file_size(value, max_size_mb=10):
    """
    Validate file size (max 10 MB by default).
    """
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            _('File size must be under %(max_size)s MB.') % {'max_size': max_size_mb}
        )