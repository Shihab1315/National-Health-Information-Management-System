from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count, Sum, F
from .permissions import has_analytics_access
from .dashboard_data import (
    get_top_stats,
    get_recent_activity,
    get_alerts,
    get_chart_data,
)
from .selectors import global_search
from .constants import CACHE_TIMEOUT
from accounts.decorators import role_required
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from prescriptions.models import Prescription
from laboratory.models import LabOrder
from pharmacy.models import Medicine
from medical_records.models import MedicalRecord

@login_required
@role_required(['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'lab_technician', 'pharmacist'])
def dashboard(request):
    """
    print("Dashboard View Executed")
    Main analytics dashboard view.
    Role‑based content is handled in the template.
    """
    # Get base data
    stats = get_top_stats()
    recent = get_recent_activity()
    alerts = get_alerts()
    charts = get_chart_data()

    # Role-specific data
    role = request.user.role
    role_data = {}

    if role == 'super_admin':
        role_data = {
            'total_hospitals': stats.get('total_hospitals', 0),
            'total_doctors': stats.get('total_doctors', 0),
            'total_patients': stats.get('total_patients', 0),
            'revenue': 0,  # Placeholder – you can calculate from sales
        }
    elif role == 'hospital_admin':
        hospital = request.user.hospital
        if hospital:
            role_data = {
                'total_doctors': Doctor.objects.filter(hospital=hospital).count(),
                'total_patients': Patient.objects.filter(hospital=hospital).count(),
                'today_appointments': Appointment.objects.filter(
                    hospital=hospital,
                    appointment_date=timezone.now().date()
                ).count(),
            }
        else:
            role_data = {
                'total_doctors': stats.get('total_doctors', 0),
                'total_patients': stats.get('total_patients', 0),
                'today_appointments': stats.get('today_appointments', 0),
            }
    elif role == 'doctor':
        doctor = Doctor.objects.filter(user=request.user).first()
        if doctor:
            role_data = {
                'today_appointments': Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=timezone.now().date()
                ).count(),
                'my_patients': Patient.objects.filter(doctor=doctor).count(),
                'pending_prescriptions': Prescription.objects.filter(
                    doctor=doctor,
                    status='pending'
                ).count(),
            }
    elif role == 'receptionist':
        hospital = request.user.hospital
        role_data = {
            'today_queue': Appointment.objects.filter(
                hospital=hospital,
                status='pending'
            ).count(),
            'today_appointments': Appointment.objects.filter(
                hospital=hospital,
                appointment_date=timezone.now().date()
            ).count(),
        }
    elif role == 'lab_technician':
        role_data = {
            'pending_tests': LabOrder.objects.filter(status='pending').count(),
            'completed_tests': LabOrder.objects.filter(status='completed').count(),
        }
    elif role == 'pharmacist':
        role_data = {
            'today_prescriptions': Prescription.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'medicine_stock': Medicine.objects.aggregate(
                total=Sum('current_stock')
            )['total'] or 0,
            'low_stock_alert': Medicine.objects.filter(
                current_stock__lte=F('minimum_stock')
            ).count(),
        }
    elif role == 'patient':
        patient = Patient.objects.filter(user=request.user).first()
        if patient:
            role_data = {
                'upcoming_appointment': Appointment.objects.filter(
                    patient=patient,
                    appointment_date__gte=timezone.now().date()
                ).order_by('appointment_date').first(),
                'prescriptions': Prescription.objects.filter(patient=patient).count(),
                'medical_history': MedicalRecord.objects.filter(patient=patient).count(),
            }

    context = {
        'stats': stats,
        'recent': recent,
        'alerts': alerts,
        'charts': charts,
        'role_data': role_data,
        'user': request.user,
    }
    return render(request, 'analytics/dashboard.html', context)


@login_required
@role_required(['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'lab_technician', 'pharmacist'])

def global_search_view(request):
    """
    AJAX endpoint for global search.
    Returns JSON results for patients, doctors, appointments, etc.
    """
    if not has_analytics_access(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': {}}, status=400)

    results = global_search(query)
    # Convert to serializable format (only necessary fields)
    serialized = {}
    for key, qs in results.items():
        serialized[key] = [
            {
                'id': item.id,
                'name': str(item),
                'url': item.get_absolute_url() if hasattr(item, 'get_absolute_url') else '#'
            }
            for item in qs
        ]
    return JsonResponse({'results': serialized})

def reports(request):
    return render(request, "analytics/reports.html")


def settings(request):
    return render(request, "analytics/settings.html")