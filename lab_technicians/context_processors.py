# lab_technicians/context_processors.py
from .models import LabTechnician

def lab_technician_context(request):
    """Add lab technician context to all templates."""
    context = {}
    
    if request.user.is_authenticated and request.user.role == 'lab_technician':
        try:
            technician = request.user.lab_technician_profile
            context['technician'] = technician
            context['hospital'] = technician.hospital
        except:
            pass
    
    return context