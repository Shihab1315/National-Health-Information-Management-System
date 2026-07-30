from django.shortcuts import render, get_object_or_404, redirect
from django.core.cache import cache
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from .services import DashboardService
from django.http import HttpResponseServerError

from .models import Hero, Service, Feature, Statistic, WhyChooseUs, Testimonial, FAQ, Partner, CTA, Footer
import logging

# Admin dashboard imports
from accounts.decorators import role_required
from appointments.models import Appointment
from doctors.models import Doctor
from hospitals.models import Hospital
from laboratory.models import LabResult   # adjust if different
from medical_records.models import MedicalRecord
from patients.models import Patient
from pharmacy.models import Medicine, Sale, SaleItem
from prescriptions.models import Prescription

try:
    from prescriptions.models import PrescriptionMedicine
except ImportError:
    PrescriptionMedicine = None
from notifications.models import Notification   # if exists
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


def get_greeting():
    """Return a greeting based on the current local time."""
    hour = timezone.localtime().hour
    if hour < 12:
        return 'Good morning'
    if hour < 18:
        return 'Good afternoon'
    return 'Good evening'


class DashboardViewMixin:
    """Mixin for common context data with caching."""
    cache_timeout = 60 * 15  # 15 minutes

    def get_home_context(self):
        # ... (unchanged, keep as is) ...
        pass


def homepage(request):
    try:
        mixin = DashboardViewMixin()
        context = mixin.get_home_context()
        return render(request, 'dashboard/homepage.html', context)
    except Exception as e:
        # Log the error (optional)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Homepage error: {e}")
        # Return a simple error page (or redirect)
        return HttpResponseServerError("Something went wrong. Please try again later.")


# ===========================================================================
# ENHANCED ADMIN DASHBOARD
# ===========================================================================
@login_required
@role_required(["super_admin", "hospital_admin"])
def admin_dashboard(request):
    """
    Enhanced Admin Dashboard – complete enterprise overview.
    """
    today = timezone.now().date()
    now = timezone.now()

    # ---------- 1. STATISTICS ----------
    total_users = User.objects.count()
    total_hospitals = Hospital.objects.count()
    total_doctors = Doctor.objects.count()
    total_patients = Patient.objects.count()

    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    pending_appointments = Appointment.objects.filter(status='pending').count() if hasattr(Appointment, 'status') else 0
    completed_appointments = Appointment.objects.filter(status='completed').count() if hasattr(Appointment, 'status') else 0

    total_medical_records = MedicalRecord.objects.count()
    total_prescriptions = Prescription.objects.count()

    total_lab_tests = LabResult.objects.count() if hasattr(LabResult, 'objects') else 0
    pending_lab_reports = LabResult.objects.filter(status='pending').count() if hasattr(LabResult, 'status') else 0

    total_medicines = Medicine.objects.count()
    low_stock_medicines = Medicine.objects.filter(current_stock__lte=F('minimum_stock')).count()
    out_of_stock_medicines = Medicine.objects.filter(current_stock=0).count()
    total_sales = Sale.objects.count()
    monthly_revenue = Sale.objects.filter(
        sale_date__month=now.month,
        sale_date__year=now.year
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # ---------- 2. CHART DATA ----------
    appointment_months, appointment_counts = [], []
    patient_months, patient_counts = [], []
    revenue_months, revenue_amounts = [], []
    medicine_sales_months, medicine_sales_counts = [], []

    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timezone.timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timezone.timedelta(days=32)).replace(day=1)

        appt_count = Appointment.objects.filter(
            appointment_date__gte=month_start,
            appointment_date__lt=month_end
        ).count()
        appointment_months.append(month_start.strftime('%b'))
        appointment_counts.append(appt_count)

        pat_count = Patient.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        patient_months.append(month_start.strftime('%b'))
        patient_counts.append(pat_count)

        rev = Sale.objects.filter(
            sale_date__gte=month_start,
            sale_date__lt=month_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        revenue_months.append(month_start.strftime('%b'))
        revenue_amounts.append(float(rev))

        qty = SaleItem.objects.filter(
            sale__sale_date__gte=month_start,
            sale__sale_date__lt=month_end
        ).aggregate(total=Sum('quantity'))['total'] or 0
        medicine_sales_months.append(month_start.strftime('%b'))
        medicine_sales_counts.append(qty)

    # ---------- 3. RECENT ACTIVITY ----------
    recent_patients = Patient.objects.select_related('user').order_by('-created_at')[:5]
    recent_doctors = Doctor.objects.select_related('hospital', 'user').order_by('-created_at')[:5]
    recent_appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-appointment_date')[:5]
    recent_prescriptions = Prescription.objects.select_related('patient', 'doctor').order_by('-created_at')[:5]

    # --- FIX: LabResult uses order_item__patient ---
    recent_lab_reports = (
    LabResult.objects
    .select_related(
        'order_item__lab_order__patient',
        'order_item__lab_order__doctor',
        'order_item__test',
    )
    .order_by('-created_at')[:5]
)

    recent_pharmacy_sales = Sale.objects.select_related('patient', 'pharmacist').order_by('-sale_date')[:5]

    # ---------- 4. ALERTS ----------
    alerts = {
        'low_stock': low_stock_medicines,
        'expired_medicines': Medicine.objects.filter(expiry_date__lt=today).count(),
        'appointments_today': today_appointments,
        'pending_lab_reports': pending_lab_reports,
        'doctors_without_hospital': Doctor.objects.filter(hospital__isnull=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'new_registrations_today': Patient.objects.filter(created_at__date=today).count(),
        'upcoming_expiry': Medicine.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timezone.timedelta(days=7)
        ).count(),
    }

    # ---------- 5. SYSTEM HEALTH ----------
    online_users = User.objects.filter(
        is_active=True,
        last_login__gte=now - timezone.timedelta(minutes=5)
    ).count() if hasattr(User, 'last_login') else 0

    system_health = {
        'database': 'Online',
        'server': 'Online',
        'laboratory': 'Online',
        'pharmacy': 'Online',
        'queue': '0',
        'online_users': online_users,
    }

    # ---------- 6. NOTIFICATIONS ----------
    recent_notifications = Notification.objects.select_related('recipient', 'sender').order_by('-created_at')[:10]

    # ---------- 7. CONTEXT ----------
    context = {
        'total_users': total_users,
        'total_hospitals': total_hospitals,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'today_appointments': today_appointments,
        'pending_appointments': pending_appointments,
        'completed_appointments': completed_appointments,
        'total_medical_records': total_medical_records,
        'total_prescriptions': total_prescriptions,
        'total_lab_tests': total_lab_tests,
        'pending_lab_reports': pending_lab_reports,
        'total_medicines': total_medicines,
        'low_stock_medicines': low_stock_medicines,
        'out_of_stock_medicines': out_of_stock_medicines,
        'total_sales': total_sales,
        'monthly_revenue': monthly_revenue,
        'appointment_months': appointment_months,
        'appointment_counts': appointment_counts,
        'patient_months': patient_months,
        'patient_counts': patient_counts,
        'revenue_months': revenue_months,
        'revenue_amounts': revenue_amounts,
        'medicine_sales_months': medicine_sales_months,
        'medicine_sales_counts': medicine_sales_counts,
        'recent_patients': recent_patients,
        'recent_doctors': recent_doctors,
        'recent_appointments': recent_appointments,
        'recent_prescriptions': recent_prescriptions,
        'recent_lab_reports': recent_lab_reports,
        'recent_pharmacy_sales': recent_pharmacy_sales,
        'alerts': alerts,
        'system_health': system_health,
        'recent_notifications': recent_notifications,
        'user': request.user,
        'current_date': timezone.now(),
    }

    return render(request, 'dashboard/admin_dashboard.html', context)

# ===========================================================================
# DOCTOR DASHBOARD
# ===========================================================================
@login_required
@role_required(['doctor'])
def doctor_dashboard(request):
    """Doctor dashboard - always uses request.user to get doctor."""
    
    # Get the logged-in doctor
    doctor = Doctor.objects.get_by_user(request.user)
    
    if not doctor:
        # This is a critical state - doctor exists but User link is broken
        messages.error(request, 
            "Your account is not properly configured as a doctor. "
            "Please contact system administrator."
        )
        return redirect('dashboard:home')
    
    # Now use the doctor instance for all queries
    appointments = Appointment.objects.filter(
        doctor=doctor
    ).select_related('patient')
    
    total_appointments = appointments.count()
    pending = appointments.filter(status='pending').count()
    confirmed = appointments.filter(status='confirmed').count()
    completed = appointments.filter(status='completed').count()
    
    # Upcoming appointments
    today = timezone.now().date()
    upcoming = appointments.filter(
        appointment_date__gte=today,
        status__in=['pending', 'confirmed']
    ).order_by('appointment_date', 'appointment_time')[:5]
    
    # Prescriptions
    prescriptions = Prescription.objects.filter(
        doctor=doctor
    ).order_by('-created_at')[:5]
    
    context = {
        'doctor': doctor,
        'total_appointments': total_appointments,
        'pending': pending,
        'confirmed': confirmed,
        'completed': completed,
        'upcoming': upcoming,
        'prescriptions': prescriptions,
    }
    
    return render(request, 'dashboard/doctor_dashboard.html', context)


# ===========================================================================
# PATIENT DASHBOARD (COMPLETE)
# ===========================================================================
@login_required
@role_required(['patient'])
def patient_dashboard(request):
    """
    Patient Dashboard – overview for a logged-in patient.
    """
    today = timezone.now().date()
    now = timezone.now()

    # Get the Patient profile associated with the logged-in user
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.error(request, 'Patient profile not found.')
        return redirect('dashboard:homepage')

    # ---------- Statistics ----------
    total_appointments = Appointment.objects.filter(patient=patient).count()

    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=today
    ).select_related('doctor', 'hospital').order_by('appointment_date', 'appointment_time')[:5]

    appointment_history = Appointment.objects.filter(
        patient=patient,
        appointment_date__lt=today
    ).select_related('doctor', 'hospital').order_by('-appointment_date')[:5]

    pending_prescriptions = Prescription.objects.filter(
        patient=patient,
        status__in=['draft', 'issued']
    ).count()

    recent_prescriptions = Prescription.objects.filter(
        patient=patient
    ).select_related('doctor').order_by('-created_at')[:5]

    # ---------- Lab Reports ----------
    if hasattr(LabResult, 'objects'):
        lab_reports = LabResult.objects.filter(
            order_item__lab_order__patient=patient
        ).select_related(
            'order_item__lab_order__doctor',
            'order_item'
        ).order_by('-created_at')[:5]
    else:
        lab_reports = []

    # Medical records
    medical_records = MedicalRecord.objects.filter(
        patient=patient
    ).order_by('-visit_date')[:5]

    # Medicine reminders
    if PrescriptionMedicine is not None:
        medicine_reminders = PrescriptionMedicine.objects.filter(
            prescription__patient=patient,
            prescription__status='issued'
        ).select_related('prescription')[:10]
    else:
        medicine_reminders = []

    # Notifications
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:10] if hasattr(Notification, 'objects') else []

    # ---------- New: Primary Doctor ----------
    primary_doctor = None
    latest_appointment = Appointment.objects.filter(patient=patient).order_by('-appointment_date').first()
    if latest_appointment and latest_appointment.doctor:
        primary_doctor = latest_appointment.doctor

    # ---------- New: Emergency Contact ----------
    emergency_contact = {
        'name': patient.emergency_contact_name or 'N/A',
        'phone': patient.emergency_contact_phone or 'N/A',
    }

    # ---------- New: Health Metrics ----------
    health_metrics = {
        'height': getattr(patient, 'height', 'N/A'),
        'weight': getattr(patient, 'weight', 'N/A'),
        'blood_pressure': getattr(patient, 'blood_pressure', 'N/A'),
        'blood_sugar': getattr(patient, 'blood_sugar', 'N/A'),
        'heart_rate': getattr(patient, 'heart_rate', 'N/A'),
        'temperature': getattr(patient, 'temperature', 'N/A'),
        'bmi': getattr(patient, 'bmi', 'N/A'),
    }

    # Health tips (static – can be extended)
    health_tips = [
        {'title': 'Stay Hydrated', 'description': 'Drink at least 8 glasses of water daily.'},
        {'title': 'Regular Exercise', 'description': '30 minutes of moderate exercise daily.'},
        {'title': 'Balanced Diet', 'description': 'Include fruits, vegetables, and proteins.'},
        {'title': 'Adequate Sleep', 'description': 'Aim for 7-8 hours of quality sleep.'},
    ]

    # ---------- Build context ----------
    context = {
        'patient': patient,
        'total_appointments': total_appointments,
        'upcoming_appointments': upcoming_appointments,
        'appointment_history': appointment_history,
        'pending_prescriptions': pending_prescriptions,
        'recent_prescriptions': recent_prescriptions,
        'lab_reports': lab_reports,
        'medical_records': medical_records,
        'medicine_reminders': medicine_reminders,
        'notifications': notifications,
        'health_tips': health_tips,
        'current_date': timezone.now(),
        'greeting': get_greeting(),
        # New variables
        'primary_doctor': primary_doctor,
        'emergency_contact': emergency_contact,
        'health_metrics': health_metrics,
        'health_score': 85,  # placeholder – can be computed from metrics later
    }

    return render(request, 'dashboard/patient_dashboard.html', context)

