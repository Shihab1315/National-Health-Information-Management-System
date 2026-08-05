# dashboard/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import F, Sum, Count
from django.http import HttpResponseServerError
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from doctors.models import Specialty
from django.db.models import Q


# ✅ সঠিক ডেকোরেটর ইমপোর্ট
from accounts.decorators import role_required
from accounts.models import User
from appointments.models import Appointment
from doctors.models import Doctor
from patients.models import Patient
from prescriptions.models import Prescription
from hospitals.models import Hospital,HospitalApplication
from medical_records.models import MedicalRecord
from laboratory.models import LabResult
from pharmacy.models import Medicine, Sale, SaleItem
from notifications.models import Notification
 
logger = logging.getLogger(__name__)


def get_greeting():
    """Return a greeting based on current time."""
    hour = timezone.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    elif 17 <= hour < 21:
        return "Good Evening"
    else:
        return "Good Night"


# ===========================================================================
# HOMEPAGE
# ===========================================================================
def homepage(request):
    """Homepage for all users."""
    try:
        context = {
            'user': request.user,
            'is_authenticated': request.user.is_authenticated,
            'site_name': 'NHIMS Bangladesh',
            'year': 2026,
        }
        
        if request.user.is_authenticated:
            context['user_name'] = request.user.get_full_name() or request.user.username
            if hasattr(request.user, 'get_role_display'):
                context['user_role'] = request.user.get_role_display()
            
            # Role-based dashboard URL
            if request.user.role == 'super_admin':
                context['dashboard_url'] = '/superadmin_d/'
            elif request.user.role == 'doctor':
                context['dashboard_url'] = '/doctor_d/'
            elif request.user.role == 'patient':
                context['dashboard_url'] = '/patient_d/'
            elif request.user.role == 'hospital_admin':
                context['dashboard_url'] = '/hospital_admin/'
            else:
                context['dashboard_url'] = '#'
        
        context['features'] = [
            {'icon': 'fa-hospital', 'title': 'Hospitals', 'desc': 'Connected nationwide'},
            {'icon': 'fa-user-md', 'title': 'Doctors', 'desc': 'Registered professionals'},
            {'icon': 'fa-users', 'title': 'Patients', 'desc': 'Served with care'},
        ]
        
        return render(request, 'dashboard/homepage.html', context)
        
    except Exception as e:
        logger.error(f"Homepage error: {str(e)}", exc_info=True)
        return render(request, 'dashboard/homepage.html', {
            'error': 'Something went wrong. Please try again later.',
            'user': request.user,
        })


# ===========================================================================
# ADMIN DASHBOARD - Super Admin & Hospital Admin
# ===========================================================================
@login_required
@role_required(['super_admin'])
def superadmin_dashboard(request):
    """
    Super Admin Dashboard - Complete enterprise overview for Super Admin only.
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
    pending_appointments = Appointment.objects.filter(status='pending').count()
    completed_appointments = Appointment.objects.filter(status='completed').count()

    total_medical_records = MedicalRecord.objects.count()
    total_prescriptions = Prescription.objects.count()

    total_lab_tests = LabResult.objects.count()
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
    recent_lab_reports = LabResult.objects.select_related(
        'order_item__lab_order__patient',
        'order_item__lab_order__doctor',
        'order_item__test',
    ).order_by('-created_at')[:5]
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

    # ---------- 7. PENDING HOSPITAL APPLICATIONS ----------
    from hospitals.models import HospitalApplication
    pending_applications = HospitalApplication.objects.filter(
        status__in=['submitted', 'under_review', 'need_more_info']
    ).count()

    # ---------- 8. CONTEXT ----------
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
        'pending_applications': pending_applications,
        'user': request.user,
        'current_date': timezone.now(),
    }

    return render(request, 'dashboard/superadmin_dashboard.html', context)


# ===========================================================================
# DOCTOR DASHBOARD
# ===========================================================================
@login_required
@role_required(['doctor'])
def doctor_dashboard(request):
    """Doctor Dashboard - only doctors."""

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect("dashboard:homepage")

    # 🔒 যদি verify না হয় তাহলে Dashboard এ ঢুকতে পারবে না
    if not doctor.is_verified:
        return redirect("doctors:verification")

    # ---------- নিচের পুরনো code ----------
    appointments = Appointment.objects.filter(
        doctor=doctor
    ).select_related('patient')

    total_appointments = appointments.count()
    pending = appointments.filter(status='pending').count()
    confirmed = appointments.filter(status='confirmed').count()
    completed = appointments.filter(status='completed').count()

    today = timezone.now().date()

    upcoming = appointments.filter(
        appointment_date__gte=today,
        status__in=['pending', 'confirmed']
    ).order_by(
        'appointment_date',
        'appointment_time'
    )[:5]

    prescriptions = Prescription.objects.filter(
        doctor=doctor
    ).order_by('-created_at')[:5]

    context = {
        'doctor': doctor,
        'is_verified': doctor.is_verified,
        'total_appointments': total_appointments,
        'pending': pending,
        'confirmed': confirmed,
        'completed': completed,
        'upcoming': upcoming,
        'prescriptions': prescriptions,
    }

    return render(request, 'dashboard/doctor_dashboard.html', context)


# ===========================================================================
# PATIENT DASHBOARD
# ===========================================================================
@login_required
@role_required(['patient'])
def patient_dashboard(request):
    """Patient Dashboard - only patients."""
    
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.error(request, 'Patient profile not found.')
        return redirect('dashboard:homepage')
    
    today = timezone.now().date()
    
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
    
    lab_reports = LabResult.objects.filter(
        order_item__lab_order__patient=patient
    ).select_related(
        'order_item__lab_order__doctor',
        'order_item'
    ).order_by('-created_at')[:5] if hasattr(LabResult, 'objects') else []
    
    medical_records = MedicalRecord.objects.filter(
        patient=patient
    ).order_by('-visit_date')[:5]
    
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:10] if hasattr(Notification, 'objects') else []
    
    emergency_contact = {
        'name': patient.emergency_contact_name or 'N/A',
        'phone': patient.emergency_contact_phone or 'N/A',
    }
    
    health_metrics = {
        'height': getattr(patient, 'height', 'N/A'),
        'weight': getattr(patient, 'weight', 'N/A'),
        'blood_pressure': getattr(patient, 'blood_pressure', 'N/A'),
        'blood_sugar': getattr(patient, 'blood_sugar', 'N/A'),
        'heart_rate': getattr(patient, 'heart_rate', 'N/A'),
        'temperature': getattr(patient, 'temperature', 'N/A'),
        'bmi': getattr(patient, 'bmi', 'N/A'),
    }
    
    health_tips = [
        {'title': 'Stay Hydrated', 'description': 'Drink at least 8 glasses of water daily.'},
        {'title': 'Regular Exercise', 'description': '30 minutes of moderate exercise daily.'},
        {'title': 'Balanced Diet', 'description': 'Include fruits, vegetables, and proteins.'},
        {'title': 'Adequate Sleep', 'description': 'Aim for 7-8 hours of quality sleep.'},
    ]
    
    context = {
        'patient': patient,
        'total_appointments': total_appointments,
        'upcoming_appointments': upcoming_appointments,
        'appointment_history': appointment_history,
        'pending_prescriptions': pending_prescriptions,
        'recent_prescriptions': recent_prescriptions,
        'lab_reports': lab_reports,
        'medical_records': medical_records,
        'notifications': notifications,
        'health_tips': health_tips,
        'current_date': timezone.now(),
        'greeting': get_greeting(),
        'emergency_contact': emergency_contact,
        'health_metrics': health_metrics,
        'health_score': 85,
    }
    
    return render(request, 'dashboard/patient_dashboard.html', context)

def lab_technician_dashboard(request):
    """Redirect to lab technician dashboard."""
    return redirect('lab_technicians:dashboard')



# def doctors_section(request):
#     """Fetch doctors with filters for homepage."""
    
#     # Base queryset
#     doctors = Doctor.objects.filter(is_active=True, is_verified=True).select_related('hospital')
    
#     # Search filters
#     doctor_name = request.GET.get('doctor_name', '')
#     if doctor_name:
#         doctors = doctors.filter(
#             Q(full_name__icontains=doctor_name) |
#             Q(user__first_name__icontains=doctor_name) |
#             Q(user__last_name__icontains=doctor_name)
#         )
    
#     specialty = request.GET.get('specialty', '')
#     if specialty:
#         doctors = doctors.filter(specialties__id=specialty)
    
#     hospital = request.GET.get('hospital', '')
#     if hospital:
#         doctors = doctors.filter(hospital_id=hospital)
    
#     district = request.GET.get('district', '')
#     if district:
#         doctors = doctors.filter(hospital__district=district)
    
#     gender = request.GET.get('gender', '')
#     if gender:
#         doctors = doctors.filter(gender=gender)
    
#     experience = request.GET.get('experience', '')
#     if experience:
#         if experience == '0-5':
#             doctors = doctors.filter(experience__gte=0, experience__lte=5)
#         elif experience == '5-10':
#             doctors = doctors.filter(experience__gte=5, experience__lte=10)
#         elif experience == '10-15':
#             doctors = doctors.filter(experience__gte=10, experience__lte=15)
#         elif experience == '15-20':
#             doctors = doctors.filter(experience__gte=15, experience__lte=20)
#         elif experience == '20+':
#             doctors = doctors.filter(experience__gte=20)
    
#     consultation_type = request.GET.get('consultation_type', '')
#     if consultation_type == 'online':
#         doctors = doctors.filter(online_consultation=True)
#     elif consultation_type == 'offline':
#         doctors = doctors.filter(online_consultation=False)
    
#     # Sort
#     sort_by = request.GET.get('sort', 'newest')
#     if sort_by == 'top_rated':
#         doctors = doctors.order_by('-rating')
#     elif sort_by == 'highest_exp':
#         doctors = doctors.order_by('-experience')
#     elif sort_by == 'lowest_fee':
#         doctors = doctors.order_by('consultation_fee')
#     elif sort_by == 'highest_fee':
#         doctors = doctors.order_by('-consultation_fee')
#     elif sort_by == 'most_reviewed':
#         doctors = doctors.order_by('-total_reviews')
#     elif sort_by == 'available_today':
#         doctors = doctors.filter(available_today=True).order_by('-rating')
#     else:  # newest
#         doctors = doctors.order_by('-created_at')
    
#     # Pagination
#     paginator = Paginator(doctors, 12)
#     page = request.GET.get('page', 1)
    
#     try:
#         doctors_page = paginator.page(page)
#     except EmptyPage:
#         doctors_page = paginator.page(paginator.num_pages)
#     except PageNotAnInteger:
#         doctors_page = paginator.page(1)
    
#     # Get filters data
#     specialties = Specialty.objects.filter(is_active=True)
#     hospitals = Hospital.objects.filter(active=True)
#     districts = Hospital.objects.exclude(district__isnull=True).exclude(district='').values_list('district', flat=True).distinct()
    
#     context = {
#         'doctors': doctors_page,
#         'specialties': specialties,
#         'hospitals': hospitals,
#         'districts': districts,
#     }
#     return render(request, 'dashboard/partials/doctors.html', context)

def homepage_doctors(request):
    """
    Homepage doctors section - shows all active verified doctors with filters.
    This is separate from the main doctor list view.
    """
    
    # Base queryset - only active and verified doctors
    doctors = Doctor.objects.filter(
        is_active=True, 
        is_verified=True
    ).select_related('hospital', 'user').prefetch_related('specialties')
    
    # ===== SEARCH =====
    search_query = request.GET.get('search', '')
    if search_query:
        doctors = doctors.filter(
            Q(full_name__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(specialties__name__icontains=search_query) |
            Q(hospital__name__icontains=search_query)
        ).distinct()
    
    # ===== FILTERS =====
    specialty_filter = request.GET.get('specialty', '')
    if specialty_filter:
        doctors = doctors.filter(specialties__id=specialty_filter)
    
    hospital_filter = request.GET.get('hospital', '')
    if hospital_filter:
        doctors = doctors.filter(hospital_id=hospital_filter)
    
    district_filter = request.GET.get('district', '')
    if district_filter:
        doctors = doctors.filter(hospital__district=district_filter)
    
    gender_filter = request.GET.get('gender', '')
    if gender_filter:
        doctors = doctors.filter(gender=gender_filter)
    
    experience_filter = request.GET.get('experience', '')
    if experience_filter:
        if experience_filter == '0-5':
            doctors = doctors.filter(experience__gte=0, experience__lte=5)
        elif experience_filter == '5-10':
            doctors = doctors.filter(experience__gte=5, experience__lte=10)
        elif experience_filter == '10-15':
            doctors = doctors.filter(experience__gte=10, experience__lte=15)
        elif experience_filter == '15-20':
            doctors = doctors.filter(experience__gte=15, experience__lte=20)
        elif experience_filter == '20+':
            doctors = doctors.filter(experience__gte=20)
    
    consultation_filter = request.GET.get('consultation', '')
    if consultation_filter == 'online':
        doctors = doctors.filter(online_consultation=True)
    elif consultation_filter == 'offline':
        doctors = doctors.filter(online_consultation=False)
    
    # ===== SORT =====
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'top_rated':
        doctors = doctors.order_by('-rating')
    elif sort_by == 'highest_exp':
        doctors = doctors.order_by('-experience')
    elif sort_by == 'lowest_fee':
        doctors = doctors.order_by('consultation_fee')
    elif sort_by == 'highest_fee':
        doctors = doctors.order_by('-consultation_fee')
    elif sort_by == 'most_reviewed':
        doctors = doctors.order_by('-total_reviews')
    elif sort_by == 'available_today':
        doctors = doctors.filter(available_today=True).order_by('-rating')
    else:  # newest
        doctors = doctors.order_by('-created_at')
    
    # ===== PAGINATION =====
    paginator = Paginator(doctors, 12)
    page = request.GET.get('page', 1)
    
    try:
        doctors_page = paginator.page(page)
    except EmptyPage:
        doctors_page = paginator.page(paginator.num_pages)
    except PageNotAnInteger:
        doctors_page = paginator.page(1)
    
    # ===== FILTER DATA =====
    specialties = Specialty.objects.filter(is_active=True)
    hospitals = Hospital.objects.filter(active=True)
    districts = Hospital.objects.exclude(
        district__isnull=True
    ).exclude(
        district=''
    ).values_list('district', flat=True).distinct()
    
    context = {
        'doctors': doctors_page,
        'search_query': search_query,
        'specialty_filter': specialty_filter,
        'hospital_filter': hospital_filter,
        'district_filter': district_filter,
        'gender_filter': gender_filter,
        'experience_filter': experience_filter,
        'consultation_filter': consultation_filter,
        'sort_by': sort_by,
        'specialties': specialties,
        'hospitals': hospitals,
        'districts': districts,
    }
    return render(request, 'dashboard/doctors.html', context)

def homepage_hospitals(request):
    """
    Homepage hospitals section - shows all hospitals with details.
    """
    
    # ===== BASE QUERYSET =====
    hospitals = Hospital.objects.filter(
        active=True,
        is_deleted=False
    ).annotate(
        # ✅ সঠিক field names ব্যবহার করুন
        doctor_count=Count('doctors', filter=Q(doctors__is_active=True, doctors__is_verified=True)),
        department_count=Count('departments', filter=Q(departments__active=True))
    )
    
    # ===== SEARCH =====
    search_query = request.GET.get('search', '')
    if search_query:
        hospitals = hospitals.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(district__icontains=search_query) |
            Q(division__icontains=search_query) |
            Q(full_address__icontains=search_query)
        )
    
    # ===== FILTERS =====
    division_filter = request.GET.get('division', '')
    if division_filter:
        hospitals = hospitals.filter(division=division_filter)
    
    district_filter = request.GET.get('district', '')
    if district_filter:
        hospitals = hospitals.filter(district=district_filter)
    
    hospital_type_filter = request.GET.get('type', '')
    if hospital_type_filter:
        hospitals = hospitals.filter(hospital_type=hospital_type_filter)
    
    # ===== SORT =====
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'name':
        hospitals = hospitals.order_by('name')
    elif sort_by == 'doctor_count':
        hospitals = hospitals.order_by('-doctor_count')
    elif sort_by == 'rating':
        hospitals = hospitals.order_by('-average_rating')
    else:  # newest
        hospitals = hospitals.order_by('-created_at')
    
    # ===== PAGINATION =====
    paginator = Paginator(hospitals, 9)
    page = request.GET.get('page', 1)
    
    try:
        hospitals_page = paginator.page(page)
    except EmptyPage:
        hospitals_page = paginator.page(paginator.num_pages)
    except PageNotAnInteger:
        hospitals_page = paginator.page(1)
    
    # ===== FILTER DATA =====
    divisions = Hospital.objects.filter(active=True, is_deleted=False).exclude(division__isnull=True).exclude(division='').values_list('division', flat=True).distinct()
    districts = Hospital.objects.filter(active=True, is_deleted=False).exclude(district__isnull=True).exclude(district='').values_list('district', flat=True).distinct()
    
    context = {
        'hospitals': hospitals_page,
        'search_query': search_query,
        'division_filter': division_filter,
        'district_filter': district_filter,
        'hospital_type_filter': hospital_type_filter,
        'sort_by': sort_by,
        'divisions': divisions,
        'districts': districts,
    }
    return render(request, 'dashboard/hospitals.html', context)

def home_hospital_details(request, pk):
    """
    Homepage hospital detail page.
    """
    # ✅ শুধু হাসপাতাল খুঁজুন - কোনো রিডাইরেক্ট নয়
    hospital = get_object_or_404(
        Hospital.objects.filter(active=True, is_deleted=False),
        id=pk
    )
    
    # ===== STATISTICS =====
    from doctors.models import Doctor
    from django.utils import timezone
    from appointments.models import Appointment
    
    total_doctors = Doctor.objects.filter(
        hospital=hospital,
        is_active=True,
        is_verified=True
    ).count()
    
    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(
        hospital=hospital,
        appointment_date=today,
        status__in=['pending', 'confirmed']
    ).count()
    
    # ===== FACILITIES =====
    facilities = []
    facility_fields = [
        ('icu', 'ICU'), ('ccu', 'CCU'), ('nicu', 'NICU'),
        ('emergency_department', 'Emergency Department'),
        ('operation_theater', 'Operation Theater'),
        ('laboratory', 'Laboratory'), ('radiology', 'Radiology'),
        ('pharmacy', 'Pharmacy'), ('ambulance_phone', 'Ambulance Service'),
        ('blood_bank', 'Blood Bank'), ('cafeteria', 'Cafeteria'),
        ('parking', 'Parking'), ('wifi', 'Free WiFi'),
        ('wheelchair_access', 'Wheelchair Access'),
        ('ct_scan', 'CT Scan'), ('mri', 'MRI'), ('x_ray', 'X-Ray'),
    ]
    
    for field, label in facility_fields:
        if hasattr(hospital, field) and getattr(hospital, field):
            facilities.append(label)
    
    # ===== CONTEXT =====
    context = {
        'hospital': hospital,
        'total_doctors': total_doctors,
        'today_appointments': today_appointments,
        'facilities': facilities,
        'page_title': hospital.name,
        'current_page': 'Hospital Detail',
    }
    return render(request, 'dashboard/hospital_detail.html', context)