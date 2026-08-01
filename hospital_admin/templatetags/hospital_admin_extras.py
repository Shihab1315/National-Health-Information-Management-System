# hospital_admin/templatetags/hospital_admin_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary."""
    return dictionary.get(key)

@register.simple_tag
def has_verification(user):
    """Check if user has hospital verification."""
    try:
        from hospitals.models import HospitalApplication
        application = HospitalApplication.objects.filter(
            hospital_admin=user,
            status='approved'
        ).first()
        return bool(application or (hasattr(user, 'hospital') and user.hospital and user.hospital.active))
    except:
        return False