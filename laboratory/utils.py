# laboratory/utils.py
"""
Utility functions for the Laboratory module.

Provides reusable helper functions for formatting, file handling,
status mapping, and other common operations across the app.
"""

import re
import uuid
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os


def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique identifier string.

    Args:
        prefix: Optional prefix string (e.g., 'LAB-', 'ORD-').
        length: Length of the random part (default: 8).

    Returns:
        str: Unique identifier (prefix + random hex string).
    """
    random_part = uuid.uuid4().hex[:length].upper()
    return f"{prefix}{random_part}" if prefix else random_part


def generate_order_number() -> str:
    """
    Generate a temporary order number (used for fallback if model's
    generate_order_number is not called). In practice, the model's
    save() method handles this, but this function can be used for
    previews or batch creation.

    Returns:
        str: Order number in format LAB-YYYYMMDD-XXXX.
    """
    today = timezone.now()
    date_part = today.strftime('%Y%m%d')
    # This is a placeholder; the model uses database count.
    # For any ad-hoc usage, we'll create a pseudo-random one.
    seq = str(uuid.uuid4().hex[:4]).upper()
    return f"LAB-{date_part}-{seq}"


def format_result_value(value, decimal_places: int = 2) -> str:
    """
    Format a numeric result value for display.

    Args:
        value: The result value (can be int, float, Decimal, or string).
        decimal_places: Number of decimal places to show.

    Returns:
        str: Formatted result string.
    """
    if value is None or value == "":
        return "—"
    try:
        if isinstance(value, (int, float, Decimal)):
            return f"{value:.{decimal_places}f}"
        # Try to parse as number
        if isinstance(value, str):
            # Remove any extra characters (e.g., '<', '>') and try to parse numeric part
            cleaned = re.sub(r'[^0-9.eE\-+]', '', value)
            if cleaned:
                num = float(cleaned)
                return f"{num:.{decimal_places}f}"
        return str(value)
    except (ValueError, TypeError):
        return str(value)


def get_result_status(result) -> dict:
    """
    Get the display status and CSS class for a lab result.

    Args:
        result: A LabResult instance.

    Returns:
        dict: Contains 'label' and 'class' for the status badge.
    """
    if not result:
        return {"label": _("No Result"), "class": "bg-slate-500/20 text-slate-300 border-slate-500/30"}

    if result.verified_by:
        return {"label": _("Verified"), "class": "bg-green-500/20 text-green-300 border-green-500/30"}

    if result.result:
        return {"label": _("Result Entered"), "class": "bg-yellow-500/20 text-yellow-300 border-yellow-500/30"}

    return {"label": _("Pending"), "class": "bg-slate-500/20 text-slate-300 border-slate-500/30"}


def get_order_status_display(status_code: str) -> str:
    """
    Get the human-readable display name for an order status code.

    Args:
        status_code: The status code (e.g., 'ordered', 'collected').

    Returns:
        str: The display label.
    """
    from .models import LabOrder  # Avoid circular import at top

    status_map = {
        str(key): str(label)
        for key, label in LabOrder.Status.choices
    }
    return str(status_map.get(status_code, status_code.title()))


def upload_report_file(file, order_number: str, test_name: str) -> str:
    """
    Save an uploaded report file with a consistent naming pattern.

    Args:
        file: The uploaded file object.
        order_number: The lab order number.
        test_name: The name of the test.

    Returns:
        str: The file path where the file was saved.
    """
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    # Sanitize test name for filename
    safe_test_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', test_name)
    filename = f"{order_number}_{safe_test_name}_{timestamp}.{file.name.split('.')[-1]}"
    path = os.path.join('laboratory/reports/', filename)
    saved_path = default_storage.save(path, ContentFile(file.read()))
    return saved_path


def get_file_extension(filename: str) -> str:
    """
    Extract the file extension from a filename.

    Args:
        filename: The full filename.

    Returns:
        str: The extension (lowercase, without the dot).
    """
    return filename.split('.')[-1].lower() if '.' in filename else ''


def is_valid_report_file(filename: str) -> bool:
    """
    Check if a file has a valid extension for laboratory reports.

    Args:
        filename: The filename to check.

    Returns:
        bool: True if extension is in allowed list.
    """
    allowed = ['pdf', 'jpg', 'jpeg', 'png']
    return get_file_extension(filename) in allowed


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a text string to a maximum length.

    Args:
        text: The text to truncate.
        max_length: Maximum number of characters.
        suffix: The suffix to add when truncated.

    Returns:
        str: Truncated text.
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_date_input(date_string: str, fallback=None):
    """
    Parse a date string from a form input (e.g., 'YYYY-MM-DD').

    Args:
        date_string: The date string.
        fallback: Default value if parsing fails.

    Returns:
        datetime.date or None.
    """
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return fallback


def parse_time_input(time_string: str, fallback=None):
    """
    Parse a time string from a form input (e.g., 'HH:MM').

    Args:
        time_string: The time string.
        fallback: Default value if parsing fails.

    Returns:
        datetime.time or None.
    """
    try:
        return datetime.strptime(time_string, '%H:%M').time()
    except (ValueError, TypeError):
        return fallback


def clean_phone_number(phone: str) -> str:
    """
    Clean a phone number by removing non-digit characters.

    Args:
        phone: The raw phone string.

    Returns:
        str: Digits-only phone number.
    """
    if not phone:
        return ""
    return re.sub(r'\D', '', phone)