import logging
import random
import re
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

try:
    import qrcode  # type: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - dependency may be missing in some environments
    qrcode = None

from django.core.files import File
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# EXISTING FUNCTION (KEPT UNCHANGED)
# ----------------------------------------------------------------------
def generate_qr_code(data):
    """Generate QR code image for medicine."""
    if qrcode is None:
        logger.error("QR code generation failed: qrcode package is not installed.")
        return None

    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, kind='PNG')
        buffer.seek(0)
        return File(buffer, name=f"qr_{data[:10]}.png")
    except Exception as e:
        logger.error(f"QR code generation failed: {e}", exc_info=True)
        return None


# ----------------------------------------------------------------------
# ADDITIVE UTILITIES (ENTERPRISE-GRADE)
# ----------------------------------------------------------------------

# -------------------- Code Generators --------------------
def generate_medicine_code():
    """Generate a unique medicine code."""
    import random
    from .models import Medicine
    for _ in range(10):
        code = f"MED-{random.randint(1000, 9999)}"
        if not Medicine.objects.filter(medicine_code=code).exists():
            return code
    raise ValueError("Unable to generate unique medicine code after 10 attempts.")


def generate_barcode():
    """Generate a unique barcode."""
    import random
    from .models import Medicine
    for _ in range(10):
        code = f"BAR-{random.randint(10000, 99999)}"
        if not Medicine.objects.filter(barcode=code).exists():
            return code
    raise ValueError("Unable to generate unique barcode after 10 attempts.")


def generate_purchase_number():
    """Generate a unique purchase order number."""
    import random
    from .models import PurchaseOrder
    for _ in range(10):
        num = f"PO-{random.randint(1000, 9999)}"
        if not PurchaseOrder.objects.filter(purchase_number=num).exists():
            return num
    raise ValueError("Unable to generate unique purchase number after 10 attempts.")


def generate_invoice_number():
    """Generate a unique sale invoice number."""
    import random
    from .models import Sale
    for _ in range(10):
        num = f"INV-{random.randint(10000, 99999)}"
        if not Sale.objects.filter(invoice_number=num).exists():
            return num
    raise ValueError("Unable to generate unique invoice number after 10 attempts.")


# -------------------- Stock Status Helpers --------------------
def get_stock_status(medicine):
    """
    Return stock status as a string: 'out', 'low', 'normal'
    """
    if medicine.current_stock == 0:
        return 'out'
    elif medicine.current_stock <= medicine.minimum_stock:
        return 'low'
    return 'normal'


def get_stock_status_display(medicine):
    """
    Return human-readable stock status.
    """
    status = get_stock_status(medicine)
    return {
        'out': 'Out of Stock',
        'low': 'Low Stock',
        'normal': 'In Stock'
    }.get(status, 'Unknown')


def get_stock_status_color(medicine):
    """
    Return color code for stock status.
    """
    status = get_stock_status(medicine)
    return {
        'out': 'red',
        'low': 'orange',
        'normal': 'green'
    }.get(status, 'gray')


# -------------------- Expiry Status Helpers --------------------
def get_expiry_status(medicine):
    """
    Return expiry status: 'expired', 'expiring_soon', 'valid'
    """
    today = timezone.now().date()
    days_until_expiry = (medicine.expiry_date - today).days

    if days_until_expiry < 0:
        return 'expired'
    elif days_until_expiry <= 30:
        return 'expiring_soon'
    return 'valid'


def get_expiry_status_display(medicine):
    """
    Return human-readable expiry status.
    """
    status = get_expiry_status(medicine)
    return {
        'expired': 'Expired',
        'expiring_soon': 'Expiring Soon',
        'valid': 'Valid'
    }.get(status, 'Unknown')


def get_expiry_status_color(medicine):
    """
    Return color code for expiry status.
    """
    status = get_expiry_status(medicine)
    return {
        'expired': 'red',
        'expiring_soon': 'orange',
        'valid': 'green'
    }.get(status, 'gray')


# -------------------- Profit Calculation Helpers --------------------
def calculate_profit(buying_price, selling_price, quantity=1):
    """
    Calculate profit margin for a single unit or multiple units.
    """
    if buying_price is None or selling_price is None:
        return Decimal('0.00')
    profit_per_unit = selling_price - buying_price
    return profit_per_unit * quantity


def calculate_profit_percentage(buying_price, selling_price):
    """
    Calculate profit percentage.
    """
    if buying_price is None or buying_price == 0:
        return Decimal('0.00')
    profit = selling_price - buying_price
    return (profit / buying_price) * 100


# -------------------- Decimal/Currency Helpers --------------------
def format_currency(amount):
    """
    Format decimal as currency string.
    """
    if amount is None:
        return '0.00'
    return f"{amount:.2f}"


def format_currency_with_symbol(amount, symbol='$'):
    """
    Format decimal as currency with symbol.
    """
    return f"{symbol}{format_currency(amount)}"


def safe_decimal(value, default=Decimal('0.00')):
    """
    Safely convert a value to Decimal.
    """
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default


# -------------------- Date/Time Helpers --------------------
def get_start_of_day(date=None):
    """
    Get datetime at start of day.
    """
    if date is None:
        date = timezone.now().date()
    return timezone.make_aware(datetime.combine(date, datetime.min.time()))


def get_end_of_day(date=None):
    """
    Get datetime at end of day.
    """
    if date is None:
        date = timezone.now().date()
    return timezone.make_aware(datetime.combine(date, datetime.max.time()))


def get_start_of_month(year=None, month=None):
    """
    Get datetime at start of month.
    """
    if year is None or month is None:
        now = timezone.now()
        year = now.year
        month = now.month
    return timezone.make_aware(datetime(year, month, 1))


def get_end_of_month(year=None, month=None):
    """
    Get datetime at end of month.
    """
    if year is None or month is None:
        now = timezone.now()
        year = now.year
        month = now.month
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    return timezone.make_aware(next_month - timedelta(seconds=1))


def days_until_expiry(expiry_date):
    """
    Calculate number of days until expiry.
    """
    if expiry_date is None:
        return None
    today = timezone.now().date()
    return (expiry_date - today).days


# -------------------- Slug Helpers --------------------
def generate_unique_slug(model, base_slug, slug_field='slug'):
    """
    Generate a unique slug for a model.
    """
    base_slug = slugify(base_slug)
    slug = base_slug
    counter = 1
    while model.objects.filter(**{slug_field: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


# -------------------- File Helpers --------------------
def get_file_extension(filename):
    """
    Get file extension from filename.
    """
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def is_allowed_file(filename, allowed_extensions):
    """
    Check if file extension is allowed.
    """
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def get_file_size_display(size_in_bytes):
    """
    Format file size for human-readable display.
    """
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"


# -------------------- Validation Helpers --------------------
def is_valid_phone(phone):
    """
    Validate phone number format.
    """
    pattern = r'^\+?[\d\s\-()]{7,20}$'
    return bool(re.match(pattern, phone))


def is_valid_email(email):
    """
    Validate email format.
    """
    if not email:
        return False
    return '@' in email and '.' in email.split('@')[-1]


# -------------------- Batch Operation Helpers --------------------
def chunk_queryset(qs, chunk_size=100):
    """
    Yield chunks of a queryset for bulk operations.
    """
    total = qs.count()
    for start in range(0, total, chunk_size):
        yield qs[start:start + chunk_size]


# -------------------- Logging Helpers --------------------
def log_action(logger_instance, level, message, *args, **kwargs):
    """
    Helper to log actions with consistent format.
    """
    log_method = getattr(logger_instance, level, logger_instance.info)
    log_method(f"[ACTION] {message}", *args, **kwargs)