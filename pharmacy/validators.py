import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone


# ----------------------------------------------------------------------
# EXISTING VALIDATORS (KEPT UNCHANGED)
# ----------------------------------------------------------------------

def validate_positive_stock(value):
    if value < 0:
        raise ValidationError('Stock cannot be negative.')


def validate_expiry_date(value):
    if value < timezone.now().date():
        raise ValidationError('Expiry date cannot be in the past.')


def validate_positive_price(value):
    if value < 0:
        raise ValidationError('Price cannot be negative.')


def validate_barcode(value):
    if not value.isdigit():
        raise ValidationError('Barcode must contain only digits.')


# ----------------------------------------------------------------------
# ADDED VALIDATORS (ENTERPRISE-GRADE)
# ----------------------------------------------------------------------

def validate_positive_quantity(value):
    """Validate that quantity is greater than zero."""
    if value <= 0:
        raise ValidationError("Quantity must be greater than zero.")


def validate_decimal_precision(value, max_digits=10, decimal_places=2):
    """Validate that a decimal value does not exceed max digits."""
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except Exception:
            raise ValidationError("Invalid decimal value.")
    # Convert to string to count digits
    str_val = f"{value:.{decimal_places}f}"
    int_part, frac_part = str_val.split('.')
    total_digits = len(int_part) + len(frac_part)
    if total_digits > max_digits:
        raise ValidationError(
            f"Value exceeds maximum allowed digits ({max_digits} total, {decimal_places} decimal places)."
        )


def validate_unique_barcode(value, exclude_id=None):
    """Ensure barcode is unique across all medicines."""
    from .models import Medicine
    qs = Medicine.objects.filter(barcode=value)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        raise ValidationError("A medicine with this barcode already exists.")


def validate_unique_medicine_code(value, exclude_id=None):
    """Ensure medicine code is unique across all medicines."""
    from .models import Medicine
    qs = Medicine.objects.filter(medicine_code=value)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        raise ValidationError("A medicine with this code already exists.")


def validate_phone_number(value):
    """Validate phone number format: digits, optional '+', spaces, hyphens, parentheses."""
    pattern = r'^\+?[\d\s\-()]{7,20}$'
    if not re.match(pattern, value):
        raise ValidationError("Enter a valid phone number (digits, spaces, hyphens, parentheses, and optional '+').")


def validate_email_format(value):
    """Basic email format check: contains '@' and a dot after it."""
    if value and ('@' not in value or '.' not in value.split('@')[-1]):
        raise ValidationError("Enter a valid email address.")


def validate_discount(value):
    """Ensure discount is not negative."""
    if value < 0:
        raise ValidationError("Discount cannot be negative.")


def validate_vat(value):
    """Ensure VAT is not negative."""
    if value < 0:
        raise ValidationError("VAT cannot be negative.")


def validate_profit_margin(buying_price, selling_price):
    """Ensure selling price is >= buying price."""
    if selling_price < buying_price:
        raise ValidationError("Selling price must be greater than or equal to buying price.")


def validate_batch_number(value):
    """Allow alphanumeric, hyphens, underscores."""
    if value and not re.match(r'^[a-zA-Z0-9\-_]+$', value):
        raise ValidationError("Batch number can only contain letters, numbers, hyphens, and underscores.")


def validate_unique_supplier_name(value, exclude_id=None):
    """Ensure supplier name is unique."""
    from .models import Supplier
    qs = Supplier.objects.filter(name=value)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        raise ValidationError("A supplier with this name already exists.")