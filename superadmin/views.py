# superadmin/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from accounts.decorators import role_required
from django.utils.decorators import method_decorator
from hospitals.models import HospitalApplication, Hospital
from accounts.models import User
from django.db.models import Sum, Count
from django.urls import reverse_lazy
from datetime import datetime, date
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
import json
import os
from django.db import transaction
from django.db import models
import random  # <-- ADD THIS IMPORT
from django.utils.text import slugify
from django.db import IntegrityError
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .forms import SuperAdminProfileForm, SuperAdminPasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q


# Try to import other models if they exist
try:
    from appointments.models import Appointment
except ImportError:
    Appointment = None

try:
    from doctors.models import Doctor
except ImportError:
    Doctor = None

try:
    from patients.models import Patient
except ImportError:
    Patient = None

try:
    from pharmacy.models import Medicine
except ImportError:
    Medicine = None

try:
    from lab.models import LabReport
except ImportError:
    LabReport = None

try:
    from billing.models import Payment
except ImportError:
    Payment = None


# =============================================================================
# DASHBOARD
# =============================================================================
@login_required
@role_required(['super_admin'])
def superadmin_dashboard(request):
    """Super Admin Dashboard."""
    
    # Get counts with proper error handling
    total_users = User.objects.count()
    total_hospitals = Hospital.objects.count()
    
    # Get doctor count if model exists
    total_doctors = Doctor.objects.count() if Doctor else 0
    
    # Get patient count if model exists
    total_patients = Patient.objects.count() if Patient else 0
    
    # Get appointment counts if model exists
    total_appointments = Appointment.objects.count() if Appointment else 0
    
    # Fix: Use appointment_date instead of date
    today_appointments = 0
    if Appointment:
        today_appointments = Appointment.objects.filter(
            appointment_date=date.today()
        ).count()
    
    # Get pending applications
    pending_applications = HospitalApplication.objects.filter(
        status__in=['submitted', 'under_review', 'need_more_info']
    ).count()
    
    # Get pending lab reports if model exists
    pending_lab_reports = LabReport.objects.filter(status='pending').count() if LabReport else 0
    
    # Fix: Use current_stock instead of quantity, and check if <= minimum_stock
    low_stock_medicines = 0
    if Medicine:
        low_stock_medicines = Medicine.objects.filter(
            current_stock__lte=models.F('minimum_stock')
        ).count()
    
    # Get monthly revenue if model exists
    monthly_revenue = 0
    if Payment:
        monthly_revenue = Payment.objects.filter(
            date__month=datetime.now().month
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get approved and rejected hospitals counts
    approved_hospitals = Hospital.objects.filter(active=True).count()
    rejected_hospitals = HospitalApplication.objects.filter(status='rejected').count()
    
    # Fix: Use expiry_date for expired medicines
    expired_medicines = 0
    if Medicine:
        expired_medicines = Medicine.objects.filter(
            expiry_date__lt=date.today()
        ).count()
    
    context = {
        'user': request.user,
        'current_date': timezone.now(),
        'total_users': total_users,
        'total_hospitals': total_hospitals,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'today_appointments': today_appointments,
        'pending_applications': pending_applications,
        'pending_lab_reports': pending_lab_reports,
        'low_stock_medicines': low_stock_medicines,
        'monthly_revenue': monthly_revenue,
        'approved_hospitals': approved_hospitals,
        'rejected_hospitals': rejected_hospitals,
        'alerts': {
            'low_stock': low_stock_medicines,
            'expired_medicines': expired_medicines,
        }
    }
    return render(request, 'dashboard/superadmin_dashboard.html', context)


@login_required
@role_required(['super_admin'])
def pending_hospital_applications_count(request):
    """API endpoint for pending applications count."""
    count = HospitalApplication.objects.filter(
        status__in=['submitted', 'under_review', 'need_more_info']
    ).count()
    return JsonResponse({'count': count})


# =============================================================================
# HOSPITAL MANAGEMENT - PENDING APPLICATIONS
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class PendingHospitalApplicationListView(View):
    """List all pending hospital applications."""
    template_name = 'superadmin/hospital_management/pending_applications.html'
    
    def get(self, request):
        applications = HospitalApplication.objects.filter(
            status__in=['submitted', 'under_review', 'need_more_info']
        ).order_by('-created_at')
        
        # Count by status for better display
        status_counts = {
            'submitted': applications.filter(status='submitted').count(),
            'under_review': applications.filter(status='under_review').count(),
            'need_more_info': applications.filter(status='need_more_info').count(),
        }
        
        context = {
            'applications': applications,
            'total_pending': applications.count(),
            'status_counts': status_counts,
            'page_title': 'Pending Applications',
            'current_page': 'Pending Applications',
            'breadcrumb': 'Hospital Management / Pending Applications',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle approval or rejection of applications."""
        application_id = request.POST.get('application_id')
        action = request.POST.get('action')
        
        application = get_object_or_404(HospitalApplication, id=application_id)
        
        if action == 'approve':
            # Approve the application
            application.status = 'approved'
            application.approved_at = timezone.now()
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.save()
            
            # Create hospital from application with correct field mappings
            hospital, created = Hospital.objects.get_or_create(
                registration_number=application.registration_number,
                defaults={
                    # Basic Information
                    'name': application.hospital_name,
                    'hospital_code': application.application_number[:10] if application.application_number else f"HOSP-{application.id}",
                    'hospital_type': application.hospital_type or 'private',
                    'established_year': None,  # Not in application model
                    
                    # Contact Information
                    'email': application.hospital_email,  # Changed from email to hospital_email
                    'phone': application.phone,
                    'emergency_phone': application.emergency_phone or '',
                    'ambulance_phone': '',  # Not in application model
                    'website': application.website or '',
                    
                    # Address Information
                    'full_address': application.full_address,
                    'division': application.division,
                    'district': application.district,
                    'upazila': application.upazila or '',
                    'city': '',  # Not directly in application model, but area might be used
                    'area': application.area or '',
                    'country': 'Bangladesh',  # Default
                    'postal_code': application.postal_code or '',
                    'latitude': application.latitude or None,
                    'longitude': application.longitude or None,
                    'google_map_link': application.google_map_link or '',
                    
                    # License & Registration
                    'license_number': application.license_number,
                    'tin': '',  # Not in application model
                    'bin': '',  # Not in application model
                    'ownership': 'private_owned',  # Default
                    
                    # Description
                    'description': application.description or '',
                    'short_description': '',  # Not in application model
                    'mission': '',  # Not in application model
                    'vision': '',  # Not in application model
                    'history': '',  # Not in application model
                    
                    # Images
                    'logo': application.logo if hasattr(application, 'logo') and application.logo else None,
                    'cover_image': None,  # Not in application model
                    
                    # Facilities - Set to False by default
                    'emergency_available': True if application.emergency_phone else False,
                    'icu': False,
                    'nicu': False,
                    'ccu': False,
                    'emergency_department': False,
                    'operation_theater': False,
                    'laboratory': False,
                    'radiology': False,
                    'mri': False,
                    'ct_scan': False,
                    'x_ray': False,
                    'ultrasound': False,
                    'blood_bank': False,
                    'pharmacy': False,
                    'vaccination_center': False,
                    'dialysis': False,
                    'cancer_unit': False,
                    'burn_unit': False,
                    'heart_center': False,
                    'eye_center': False,
                    'dental_unit': False,
                    
                    # Amenities
                    'parking': False,
                    'wheelchair_access': False,
                    'prayer_room': False,
                    'cafeteria': False,
                    'atm': False,
                    'wifi': False,
                    'generator_backup': False,
                    'oxygen_plant': False,
                    'open_24_hours': False,
                    
                    # Statistics
                    'total_doctors': 0,
                    'total_nurses': 0,
                    'total_beds': 0,
                    'available_beds': 0,
                    'icu_beds': 0,
                    'emergency_beds': 0,
                    
                    # Status & Timestamps
                    'verified': False,
                    'featured': False,
                    'active': True,
                    'created_at': application.created_at,
                    'is_deleted': False,
                }
            )
            
            if created:
                messages.success(request, f'Hospital "{application.hospital_name}" has been approved and created successfully!')
            else:
                messages.warning(request, f'Hospital "{application.hospital_name}" already exists. Application approved.')
            
        elif action == 'reject':
            application.status = 'rejected'
            application.rejected_at = timezone.now()
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.rejection_reason = request.POST.get('rejection_reason', '')
            application.save()
            messages.warning(request, f'Application "{application.hospital_name}" has been rejected.')
            
        elif action == 'more_info':
            application.status = 'need_more_info'
            application.admin_remarks = request.POST.get('admin_remarks', '')
            application.save()
            messages.info(request, f'Requested more information for "{application.hospital_name}".')
        
        return redirect('superadmin:pending_hospital_applications')


# =============================================================================
# HOSPITAL MANAGEMENT - APPROVED HOSPITALS
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class ApprovedHospitalListView(View):
    """List all approved hospitals."""
    template_name = 'superadmin/hospital_management/approved_hospitals.html'
    
    def get(self, request):
        hospitals = Hospital.objects.filter(active=True).order_by('-created_at')
        
        context = {
            'hospitals': hospitals,
            'total_approved': hospitals.count(),
            'page_title': 'Approved Hospitals',
            'current_page': 'Approved Hospitals',
            'breadcrumb': 'Hospital Management / Approved Hospitals',
        }
        return render(request, self.template_name, context)


# =============================================================================
# HOSPITAL MANAGEMENT - REJECTED HOSPITALS
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class RejectedHospitalListView(View):
    """List all rejected hospitals."""
    template_name = 'superadmin/hospital_management/rejected_hospitals.html'
    
    def get(self, request):
        applications = HospitalApplication.objects.filter(
            status='rejected'
        ).order_by('-created_at')
        
        context = {
            'applications': applications,
            'total_rejected': applications.count(),
            'page_title': 'Rejected Hospitals',
            'current_page': 'Rejected Hospitals',
            'breadcrumb': 'Hospital Management / Rejected Hospitals',
        }
        return render(request, self.template_name, context)


# =============================================================================
# HOSPITAL MANAGEMENT - ALL HOSPITALS
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class AllHospitalListView(View):
    """List all hospitals."""
    template_name = 'superadmin/hospital_management/all_hospitals.html'
    
    def get(self, request):
        all_hospitals = Hospital.objects.all().order_by('-created_at')
        
        context = {
            'hospitals': all_hospitals,
            'total_hospitals': all_hospitals.count(),
            'page_title': 'All Hospitals',
            'current_page': 'All Hospitals',
            'breadcrumb': 'Hospital Management / All Hospitals',
        }
        return render(request, self.template_name, context)


# =============================================================================
# HOSPITAL DETAILS VIEW
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class HospitalDetailView(View):
    """View hospital details."""
    template_name = 'superadmin/hospital_management/hospital_detail.html'
    
    def get(self, request, hospital_id):
        hospital = get_object_or_404(Hospital, id=hospital_id)
        
        context = {
            'hospital': hospital,
            'page_title': hospital.name,
            'current_page': 'Hospital Details',
            'breadcrumb': f'Hospital Management / {hospital.name}',
        }
        return render(request, self.template_name, context)


# =============================================================================
# HOSPITAL MANAGEMENT - UPDATE STATUS
# =============================================================================
@login_required
@role_required(['super_admin'])
def update_hospital_status(request, hospital_id):
    """Update hospital status (activate/deactivate)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    hospital = get_object_or_404(Hospital, id=hospital_id)
    action = request.POST.get('action')
    
    if action == 'activate':
        hospital.active = True
        messages.success(request, f'Hospital "{hospital.name}" has been activated.')
    elif action == 'deactivate':
        hospital.active = False
        messages.warning(request, f'Hospital "{hospital.name}" has been deactivated.')
    else:
        messages.error(request, 'Invalid action.')
        return redirect('superadmin:all_hospitals')
    
    hospital.save()
    return redirect('superadmin:all_hospitals')


# =============================================================================
# HOSPITAL APPLICATION DETAIL VIEW
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class HospitalApplicationDetailView(View):
    """View hospital application details."""
    template_name = 'superadmin/hospital_management/application_detail.html'
    
    def get(self, request, application_id):
        application = get_object_or_404(HospitalApplication, id=application_id)
        
        # Get timeline events
        timeline = self.get_timeline(application)
        
        context = {
            'application': application,
            'timeline': timeline,
            'page_title': f'Application: {application.hospital_name}',
            'current_page': 'Application Details',
            'breadcrumb': f'Hospital Management / Pending Applications / {application.hospital_name}',
        }
        return render(request, self.template_name, context)
    
    def get_timeline(self, application):
        """Generate timeline events for the application."""
        timeline_events = []
        
        # Submission event
        if application.created_at:
            timeline_events.append({
                'status': 'submitted',
                'title': 'Application Submitted',
                'description': f'Application submitted by {application.hospital_admin.get_full_name() or application.hospital_admin.username}',
                'timestamp': application.created_at,
                'icon': 'fa-paper-plane',
                'color': 'blue'
            })
        
        # Submission event with submitted_at
        if application.submitted_at and application.submitted_at != application.created_at:
            timeline_events.append({
                'status': 'submitted',
                'title': 'Application Submitted',
                'description': f'Application submitted by {application.hospital_admin.get_full_name() or application.hospital_admin.username}',
                'timestamp': application.submitted_at,
                'icon': 'fa-paper-plane',
                'color': 'blue'
            })
        
        # Status change events
        if application.status == 'under_review' and application.reviewed_at:
            timeline_events.append({
                'status': 'under_review',
                'title': 'Under Review',
                'description': f'Application is being reviewed by {application.reviewed_by.get_full_name() or application.reviewed_by.username if application.reviewed_by else "Admin"}',
                'timestamp': application.reviewed_at,
                'icon': 'fa-spinner',
                'color': 'yellow'
            })
        
        if application.status == 'need_more_info' and application.updated_at:
            timeline_events.append({
                'status': 'need_more_info',
                'title': 'More Information Requested',
                'description': f'Additional information requested: {application.admin_remarks or "Please provide more details"}',
                'timestamp': application.updated_at,
                'icon': 'fa-info-circle',
                'color': 'purple'
            })
        
        if application.status == 'approved' and application.approved_at:
            timeline_events.append({
                'status': 'approved',
                'title': 'Application Approved',
                'description': f'Approved by {application.reviewed_by.get_full_name() or application.reviewed_by.username if application.reviewed_by else "Admin"}',
                'timestamp': application.approved_at,
                'icon': 'fa-check-circle',
                'color': 'green'
            })
        
        if application.status == 'rejected' and application.rejected_at:
            timeline_events.append({
                'status': 'rejected',
                'title': 'Application Rejected',
                'description': f'Rejected by {application.reviewed_by.get_full_name() or application.reviewed_by.username if application.reviewed_by else "Admin"}',
                'timestamp': application.rejected_at,
                'icon': 'fa-times-circle',
                'color': 'red'
            })
        
        # Sort by timestamp
        timeline_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return timeline_events

import traceback
# =============================================================================
# APPLICATION ACTIONS
# =============================================================================
@login_required
@role_required(['super_admin'])
def approve_application(request, application_id):
    """Approve a hospital application."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    application = get_object_or_404(HospitalApplication, id=application_id)

    try:
        with transaction.atomic():

            # -----------------------------
            # Update application status
            # -----------------------------
            application.status = "approved"
            application.approved_at = timezone.now()
            application.reviewed_at = timezone.now()
            application.reviewed_by = request.user
            application.save()

            # -----------------------------
            # Check existing hospital
            # -----------------------------
            hospital = Hospital.objects.filter(
                registration_number=application.registration_number
            ).first()

            # -----------------------------
            # Create hospital if not exists
            # -----------------------------
            if not hospital:

                base_slug = slugify(application.hospital_name)
                slug = base_slug
                counter = 1

                while Hospital.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                hospital_code = f"HOSP-{random.randint(1000,9999)}"
                while Hospital.objects.filter(hospital_code=hospital_code).exists():
                    hospital_code = f"HOSP-{random.randint(1000,9999)}"

                hospital = Hospital.objects.create(
                    name=application.hospital_name,
                    slug=slug,
                    hospital_code=hospital_code,
                    hospital_type=application.hospital_type or "private",
                    registration_number=application.registration_number,
                    license_number=application.license_number or "",

                    email=application.hospital_email,
                    phone=application.phone,
                    emergency_phone=application.emergency_phone or "",
                    website=application.website or "",

                    full_address=application.full_address,
                    division=application.division,
                    district=application.district,
                    upazila=application.upazila or "",
                    city=application.area or "",
                    area=application.area or "",
                    country="Bangladesh",
                    postal_code=application.postal_code or "",
                    latitude=application.latitude,
                    longitude=application.longitude,
                    google_map_link=application.google_map_link or "",

                    description=application.description or "",
                    logo=application.logo if application.logo else None,

                    emergency_available=bool(application.emergency_phone),

                    active=True,
                    verified=True,
                    featured=False,
                    is_deleted=False,
                )

                print("✅ Hospital created:", hospital.id)

            else:
                print("✅ Existing hospital found:", hospital.id)

            # ==================================================
            # Link User -> Hospital
            # ==================================================
            hospital_admin = application.hospital_admin
            hospital_admin.hospital = hospital
            hospital_admin.save(update_fields=["hospital"])

            print("✅ User linked:", hospital_admin.username)

            # ==================================================
            # Link HospitalAdminProfile -> Hospital
            # ==================================================
            from hospital_admin.models import HospitalAdminProfile

            profile, created = HospitalAdminProfile.objects.get_or_create(
                user=hospital_admin,
                defaults={
                    "hospital": hospital,
                    "full_name": hospital_admin.get_full_name() or hospital_admin.username,
                    "phone": getattr(hospital_admin, "phone", ""),
                    "is_active": True,
                },
            )

            if not created:
                profile.hospital = hospital
                profile.is_active = True
                profile.save(update_fields=["hospital", "is_active"])

            print("✅ HospitalAdminProfile linked")

            messages.success(
                request,
                f'Hospital "{hospital.name}" approved successfully.'
            )

    except Exception as e:
        print(traceback.format_exc())
        messages.error(request, str(e))

    return redirect("superadmin:pending_hospital_applications")


@login_required
@role_required(['super_admin'])
def reject_application(request, application_id):
    """Reject a hospital application."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    application = get_object_or_404(HospitalApplication, id=application_id)
    
    # Get rejection reason from POST data (not JSON)
    reason = request.POST.get('reason', '')
    
    if not reason:
        # If using JSON, also check that
        if request.content_type == 'application/json':
            try:
                import json
                data = json.loads(request.body)
                reason = data.get('reason', '')
            except:
                pass
        
        if not reason:
            messages.error(request, 'Rejection reason is required.')
            return redirect('superadmin:pending_hospital_applications')
    
    application.status = 'rejected'
    application.rejected_at = timezone.now()
    application.reviewed_by = request.user
    application.reviewed_at = timezone.now()
    application.admin_remarks = reason
    application.save()
    
    messages.warning(request, f'Application "{application.hospital_name}" has been rejected.')
    
    # If it's an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Application rejected successfully'})
    
    return redirect('superadmin:pending_hospital_applications')


@login_required
@role_required(['super_admin'])
def request_more_info(request, application_id):
    """Request more information from the applicant."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    application = get_object_or_404(HospitalApplication, id=application_id)
    
    # Get message from POST data (not JSON)
    message = request.POST.get('message', '')
    
    if not message:
        # If using JSON, also check that
        if request.content_type == 'application/json':
            try:
                import json
                data = json.loads(request.body)
                message = data.get('message', '')
            except:
                pass
        
        if not message:
            messages.error(request, 'Message is required.')
            return redirect('superadmin:pending_hospital_applications')
    
    application.status = 'need_more_info'
    application.admin_remarks = message
    application.updated_at = timezone.now()
    application.save()
    
    messages.info(request, f'More information requested for "{application.hospital_name}".')
    
    # If it's an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'More information requested successfully'})
    
    return redirect('superadmin:pending_hospital_applications')


# =============================================================================
# LOGOUT
# =============================================================================
@login_required
def superadmin_logout(request):
    """Logout super admin."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


# =============================================================================
# USER MANAGEMENT - ALL USERS
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class AllUsersView(View):
    """List all users with search and filter functionality."""
    template_name = 'superadmin/user_management/all_users.html'
    
    def get(self, request):
        # Get all users
        users = User.objects.all().order_by('-date_joined')
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(hospital__name__icontains=search_query)
            )
        
        # Role filter
        role_filter = request.GET.get('role', '')
        if role_filter:
            users = users.filter(role=role_filter)
        
        # Status filter
        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
        
        # Get the current user to exclude from deactivation
        current_user = request.user
        
        # Pagination
        paginator = Paginator(users, 20)
        page = request.GET.get('page', 1)
        
        try:
            users_page = paginator.page(page)
        except PageNotAnInteger:
            users_page = paginator.page(1)
        except EmptyPage:
            users_page = paginator.page(paginator.num_pages)
        
        # Get role choices for filter
        role_choices = User.Role.choices
        
        context = {
            'users': users_page,
            'search_query': search_query,
            'role_filter': role_filter,
            'status_filter': status_filter,
            'role_choices': role_choices,
            'current_user': current_user,
            'total_users': users.count(),
            'page_title': 'All Users',
            'current_page': 'All Users',
            'breadcrumb': 'User Management / All Users',
        }
        return render(request, self.template_name, context)


# =============================================================================
# USER DETAIL VIEW
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class UserDetailView(View):
    """View user details."""
    template_name = 'superadmin/user_management/user_detail.html'
    
    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        current_user = request.user
        
        # Get user's hospital if they have one
        hospital = user.hospital if hasattr(user, 'hospital') else None
        
        context = {
            'user': user,
            'hospital': hospital,
            'current_user': current_user,
            'page_title': f'{user.get_full_name() or user.username}',
            'current_page': 'User Details',
            'breadcrumb': f'User Management / {user.get_full_name() or user.username}',
        }
        return render(request, self.template_name, context)


# =============================================================================
# TOGGLE USER STATUS
# =============================================================================
@login_required
@role_required(['super_admin'])
def toggle_user_status(request, user_id):
    """Activate or deactivate a user."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    target_user = get_object_or_404(User, id=user_id)
    current_user = request.user
    
    # Prevent deactivating self
    if target_user.id == current_user.id:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('superadmin:all_users')
    
    # Prevent deactivating the last super admin
    if target_user.role == User.Role.SUPER_ADMIN:
        super_admin_count = User.objects.filter(
            role=User.Role.SUPER_ADMIN, 
            is_active=True
        ).count()
        if super_admin_count <= 1:
            messages.error(request, 'Cannot deactivate the last active Super Admin.')
            return redirect('superadmin:all_users')
    
    action = request.POST.get('action')
    
    if action == 'activate':
        target_user.is_active = True
        target_user.save()
        messages.success(request, f'User "{target_user.get_full_name() or target_user.username}" has been activated.')
    elif action == 'deactivate':
        target_user.is_active = False
        target_user.save()
        messages.warning(request, f'User "{target_user.get_full_name() or target_user.username}" has been deactivated.')
    else:
        messages.error(request, 'Invalid action.')
    
    return redirect('superadmin:all_users')

# =============================================================================
# SETTINGS - PROFILE
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class SuperAdminProfileView(View):
    """Super Admin profile settings."""
    template_name = 'superadmin/settings/profile.html'
    
    def get(self, request):
        form = SuperAdminProfileForm(instance=request.user)
        context = {
            'form': form,
            'user': request.user,
            'page_title': 'My Profile',
            'current_page': 'My Profile',
            'breadcrumb': 'Settings / My Profile',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = SuperAdminProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            # Check if email is unique (excluding current user)
            email = form.cleaned_data.get('email')
            if email and User.objects.exclude(id=request.user.id).filter(email=email).exists():
                form.add_error('email', 'This email is already registered.')
                context = {
                    'form': form,
                    'user': request.user,
                    'page_title': 'My Profile',
                    'current_page': 'My Profile',
                    'breadcrumb': 'Settings / My Profile',
                }
                return render(request, self.template_name, context)
            
            # Save the form
            user = form.save(commit=False)
            
            # Handle profile picture
            if 'profile_picture' in request.FILES:
                # Delete old profile picture if exists
                if user.profile_picture and os.path.isfile(user.profile_picture.path):
                    os.remove(user.profile_picture.path)
                user.profile_picture = request.FILES['profile_picture']
            
            user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('superadmin:profile')
        
        context = {
            'form': form,
            'user': request.user,
            'page_title': 'My Profile',
            'current_page': 'My Profile',
            'breadcrumb': 'Settings / My Profile',
        }
        return render(request, self.template_name, context)


# =============================================================================
# SETTINGS - CHANGE PASSWORD
# =============================================================================
@method_decorator([login_required, role_required(['super_admin'])], name='dispatch')
class SuperAdminChangePasswordView(PasswordChangeView):
    """Super Admin password change view."""
    template_name = 'superadmin/settings/change_password.html'
    form_class = SuperAdminPasswordChangeForm
    success_url = reverse_lazy('superadmin:profile')
    
    def form_valid(self, form):
        """Update session auth hash to keep user logged in."""
        user = form.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, 'Password changed successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Change Password',
            'current_page': 'Change Password',
            'breadcrumb': 'Settings / Change Password',
        })
        return context