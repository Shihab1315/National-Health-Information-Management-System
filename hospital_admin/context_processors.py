# hospital_admin/context_processors.py
from hospitals.models import HospitalApplication

def hospital_admin_context(request):
    """Add hospital admin context to all templates."""
    context = {
        'is_verified': False,
        'application': None,
    }
    
    if request.user.is_authenticated and request.user.role == 'hospital_admin':
        # Get application
        application = HospitalApplication.objects.filter(
            hospital_admin=request.user
        ).order_by('-created_at').first()
        
        # Check verification
        is_verified = False
        if application and application.status == 'approved':
            is_verified = True
        elif hasattr(request.user, 'hospital') and request.user.hospital and request.user.hospital.active:
            is_verified = True
        
        context['is_verified'] = is_verified
        context['application'] = application
    
    return context