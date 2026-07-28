# laboratory/context_processors.py
"""
Context processors for the Laboratory module.

Adds laboratory‑related variables to all templates.
"""

from django.conf import settings


def laboratory_context(request):
    """
    Add laboratory‑specific variables to every template context.

    Returns:
        dict: A dictionary containing:
            - lab_name: The name of the laboratory (from settings or default).
            - lab_version: Version string (can be used for branding).
            - lab_show_notifications: Whether to show notifications (default False).
    """
    return {
        'lab_name': getattr(settings, 'LAB_NAME', 'NHIMS Laboratory'),
        'lab_version': getattr(settings, 'LAB_VERSION', '1.0.0'),
        'lab_show_notifications': getattr(settings, 'LAB_SHOW_NOTIFICATIONS', False),
    }