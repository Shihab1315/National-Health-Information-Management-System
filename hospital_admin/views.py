# hospital_admin/views.py - Add the HospitalInformationView

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
import json
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import ProfileForm, CustomPasswordChangeForm, NotificationPreferencesForm

from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from accounts.decorators import role_required
from hospitals.models import HospitalApplication, Hospital
from django.utils import timezone
from hospitals.models import Room
from appointments.models import Appointment
from datetime import datetime, timedelta

from .forms import (
    HospitalInformationForm,
    HospitalContactInformationForm,
    HospitalAddressInformationForm,
    HospitalDocumentsForm,
    DepartmentForm,EditDepartmentForm
)
from doctors.models import Doctor,Specialty
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from hospitals.models import HospitalDepartment
from doctors.models import Doctor
from django.db.models import Count
try:
    from doctors.models import Doctor
except ImportError:
    Doctor = None


# =============================================================================
# BASE VIEW WITH VERIFICATION CHECK
# =============================================================================
# hospital_admin/views.py - Update the check_verification method

class HospitalAdminBaseView(View):
    """Base view for Hospital Admin with verification check."""
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to continue.')
            return redirect('accounts:login')
        
        # Check if user is hospital admin
        if request.user.role != 'hospital_admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('accounts:login')
        
        # Check hospital verification status
        self.application = self.get_application(request.user)
        self.is_verified = self.check_verification(request.user)
        
        # Debug print
        print(f"🔍 is_verified: {self.is_verified}")
        print(f"🔍 application status: {self.application.status if self.application else 'None'}")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_application(self, user):
        """Get the hospital application for the user."""
        try:
            return HospitalApplication.objects.filter(
                hospital_admin=user
            ).order_by('-created_at').first()
        except:
            return None
    
    def check_verification(self, user):
        """Check if hospital is verified."""
        # Check if user has a hospital assigned
        if hasattr(user, 'hospital') and user.hospital and user.hospital.active:
            return True
        
        # Check if application is approved
        application = self.get_application(user)
        if application and application.status == 'approved':
            return True
        
        return False


# =============================================================================
# HOSPITAL ADMIN DASHBOARD
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class HospitalAdminDashboardView(HospitalAdminBaseView):
    """Hospital Admin Dashboard."""
    template_name = 'hospital_admin/dashboard.html'
    
    def get(self, request):
        application = self.get_application(request.user)
        is_verified = self.check_verification(request.user)
        
        # Get application status info
        status_info = self.get_status_info(application)
        
        context = {
            'user': request.user,
            'application': application,
            'is_verified': is_verified,
            'status_info': status_info,
            'page_title': 'Dashboard',
            'current_page': 'Dashboard',
            'breadcrumb': 'Dashboard',
        }
        return render(request, self.template_name, context)
    
    def get_status_info(self, application):
        """Get application status information."""
        if not application:
            return {
                'status': 'no_application',
                'label': 'Not Submitted',
                'color': 'gray',
                'message': 'You have not submitted any hospital application yet. Start the verification process to get your hospital verified.',
                'button_text': 'Start Verification',
                'button_url': 'hospital_admin:verification',
                'button_disabled': False,
            }
        
        status_map = {
            'draft': {
                'status': 'draft',
                'label': 'Draft',
                'color': 'gray',
                'message': 'Your hospital application is in draft mode. Complete all sections and submit for review.',
                'button_text': 'Continue Verification',
                'button_url': 'hospital_admin:verification',
                'button_disabled': False,
            },
            'submitted': {
                'status': 'submitted',
                'label': 'Submitted',
                'color': 'yellow',
                'message': 'Your application has been submitted successfully. The Super Admin will review it shortly.',
                'button_text': 'Under Review',
                'button_url': '#',
                'button_disabled': True,
            },
            'under_review': {
                'status': 'under_review',
                'label': 'Under Review',
                'color': 'orange',
                'message': 'Your application is currently being reviewed by the Super Admin. Please wait for their decision.',
                'button_text': 'Under Review',
                'button_url': '#',
                'button_disabled': True,
            },
            'need_more_info': {
                'status': 'need_more_info',
                'label': 'Need More Info',
                'color': 'amber',
                'message': 'The Super Admin has requested additional information. Please review the remarks and update your application.',
                'button_text': 'Edit Application',
                'button_url': 'hospital_admin:verification',
                'button_disabled': False,
            },
            'rejected': {
                'status': 'rejected',
                'label': 'Rejected',
                'color': 'red',
                'message': 'Your application has been rejected. Please review the rejection reason and resubmit with necessary changes.',
                'button_text': 'Update & Resubmit',
                'button_url': 'hospital_admin:verification',
                'button_disabled': False,
            },
            'approved': {
                'status': 'approved',
                'label': 'Verified',
                'color': 'green',
                'message': 'Congratulations! Your hospital has been verified successfully. All features are now unlocked.',
                'button_text': 'Go to Dashboard',
                'button_url': 'hospital_admin:dashboard',
                'button_disabled': False,
            },
        }
        
        return status_map.get(application.status, status_map['draft'])


# =============================================================================
# HOSPITAL VERIFICATION PAGE (PLACEHOLDER)
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class HospitalVerificationView(HospitalAdminBaseView):
    """Hospital Verification placeholder page."""
    template_name = 'hospital_admin/verification.html'
    
    def get(self, request):
        application = self.get_application(request.user)
        is_verified = self.check_verification(request.user)
        
        # If already verified, redirect to dashboard
        if is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # Check if application exists, if not create a draft
        if not application:
            application = HospitalApplication.objects.create(
                hospital_admin=request.user,
                status='draft',
                hospital_name='',
                hospital_type='general',
                license_number='',
                registration_number='',
                admin_name=request.user.get_full_name() or request.user.username,
                admin_email=request.user.email,
                admin_phone=request.user.phone or '',
                terms_accepted=False,
            )
            messages.info(request, 'A new draft application has been created. Please complete the verification process.')
        
        context = {
            'user': request.user,
            'application': application,
            'is_verified': is_verified,
            'page_title': 'Hospital Verification',
            'current_page': 'Hospital Verification',
            'breadcrumb': 'Hospital Verification',
        }
        return render(request, self.template_name, context)


# =============================================================================
# HOSPITAL INFORMATION VIEW
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class HospitalInformationView(HospitalAdminBaseView):
    """Step 1: Hospital Information."""
    template_name = 'hospital_admin/verification/hospital_information.html'
    
    def get(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        form = HospitalInformationForm(instance=application)
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 1,
            'total_steps': 5,
            'page_title': 'Hospital Information',
            'current_page': 'Hospital Information',
            'breadcrumb': 'Verification / Hospital Information',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        form = HospitalInformationForm(request.POST, instance=application)
        
        if form.is_valid():
            # Save the form but keep status as draft
            application = form.save(commit=False)
            application.status = 'draft'
            application.save()
            
            messages.success(request, 'Hospital information saved successfully!')
            
            # Determine action - FIXED: Redirect to contact page
            if 'save_continue' in request.POST:
                return redirect('/hospital-admin/verification/contact-information/')
            elif 'save_draft' in request.POST:
                messages.info(request, 'Your progress has been saved. You can continue later.')
                return redirect('hospital_admin:dashboard')
            else:
                return redirect('hospital_admin:dashboard')
        
        # Form has errors
        messages.error(request, 'Please correct the highlighted errors.')
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 1,
            'total_steps': 5,
            'page_title': 'Hospital Information',
            'current_page': 'Hospital Information',
            'breadcrumb': 'Verification / Hospital Information',
        }
        return render(request, self.template_name, context)
    
    def get_or_create_application(self, user):
        """Get existing application or create a new draft."""
        application = HospitalApplication.objects.filter(
            hospital_admin=user
        ).order_by('-created_at').first()
        
        if not application:
            # Create a new draft application
            application = HospitalApplication.objects.create(
                hospital_admin=user,
                status='draft',
                hospital_name='',
                hospital_type='general',
                license_number='',
                registration_number='',
                admin_name=user.get_full_name() or user.username,
                admin_email=user.email,
                admin_phone=user.phone or '',
                terms_accepted=False,
            )
        
        return application

# =============================================================================
# LOCKED MODULE VIEW
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class LockedModuleView(HospitalAdminBaseView):
    """View for locked modules."""
    
    def get(self, request, *args, **kwargs):
        is_verified = self.check_verification(request.user)
        
        # Check if hospital is verified
        if not is_verified:
            messages.warning(request, 'Complete hospital verification first to access this module.')
            return redirect('hospital_admin:dashboard')
        
        # If verified, redirect to the actual module (to be implemented)
        messages.info(request, 'This module will be available in the next update.')
        return redirect('hospital_admin:dashboard')


# =============================================================================
# Helper Functions
# =============================================================================
def get_hospital_admin_context(user):
    """Get context data for hospital admin."""
    application = HospitalApplication.objects.filter(
        hospital_admin=user
    ).order_by('-created_at').first()
    
    is_verified = False
    if application and application.status == 'approved':
        is_verified = True
    elif hasattr(user, 'hospital') and user.hospital and user.hospital.active:
        is_verified = True
    
    return {
        'application': application,
        'is_verified': is_verified,
    }
    
# =============================================================================
# HOSPITAL CONTACT INFORMATION VIEW
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class HospitalVerificationContactView(HospitalAdminBaseView):
    """Step 2: Contact Information."""
    template_name = 'hospital_admin/verification/contact_information.html'
    
    def get(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # Check if Step 1 is complete (has hospital_name)
        if not application.hospital_name:
            messages.warning(request, 'Please complete Step 1: Hospital Information first.')
            return redirect('hospital_admin:hospital_information')
        
        form = HospitalContactInformationForm(instance=application)
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 2,
            'total_steps': 5,
            'page_title': 'Contact Information',
            'current_page': 'Contact Information',
            'breadcrumb': 'Verification / Contact Information',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # Check if Step 1 is complete (has hospital_name)
        if not application.hospital_name:
            messages.warning(request, 'Please complete Step 1: Hospital Information first.')
            return redirect('hospital_admin:hospital_information')
        
        form = HospitalContactInformationForm(request.POST, instance=application)
        
        if form.is_valid():
            # Save the form but keep status as draft
            application = form.save(commit=False)
            application.status = 'draft'
            application.save()
            
            messages.success(request, 'Contact information saved successfully!')
            
            # Determine action - FIXED: Use correct URL name
            if 'save_continue' in request.POST:
                # Redirect to Step 3 - Address (will be implemented later)
                # For now, redirect back to contact with a message
                messages.info(request, 'Step 3: Address Information will be available in the next update.')
                return redirect('/hospital-admin/verification/address-information/')
            elif 'save_draft' in request.POST:
                return redirect('hospital_admin:dashboard')
            else:
                return redirect('hospital_admin:verification_contact_information')
        
        # Form has errors
        messages.error(request, 'Please correct the highlighted errors.')
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 2,
            'total_steps': 5,
            'page_title': 'Contact Information',
            'current_page': 'Contact Information',
            'breadcrumb': 'Verification / Contact Information',
        }
        return render(request, self.template_name, context)
    
    def get_or_create_application(self, user):
        """Get existing application or create a new draft."""
        application = HospitalApplication.objects.filter(
            hospital_admin=user
        ).order_by('-created_at').first()
        
        if not application:
            # Create a new draft application
            application = HospitalApplication.objects.create(
                hospital_admin=user,
                status='draft',
                hospital_name='',
                hospital_type='general',
                license_number='',
                registration_number='',
                admin_name=user.get_full_name() or user.username,
                admin_email=user.email,
                admin_phone=user.phone or '',
                terms_accepted=False,
            )
        
        return application
    
# hospital_admin/views.py - Update the address view

# =============================================================================
# HOSPITAL ADDRESS INFORMATION VIEW
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class HospitalVerificationAddressView(HospitalAdminBaseView):
    """Step 3: Address Information."""
    template_name = 'hospital_admin/verification/address_information.html'
    
    def get(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # Check if Step 1 is complete (has hospital_name)
        if not application.hospital_name:
            messages.warning(request, 'Please complete Step 1: Hospital Information first.')
            return redirect('/hospital-admin/verification/hospital-information/')
        
        # Check if Step 2 is complete (has hospital_email)
        if not application.hospital_email:
            messages.warning(request, 'Please complete Step 2: Contact Information first.')
            return redirect('/hospital-admin/verification/contact-information/')
        
        form = HospitalAddressInformationForm(instance=application)
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 3,
            'total_steps': 5,
            'progress_percentage': 60,
            'page_title': 'Address Information',
            'current_page': 'Address Information',
            'breadcrumb': 'Verification / Address Information',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # Check if Step 1 is complete (has hospital_name)
        if not application.hospital_name:
            messages.warning(request, 'Please complete Step 1: Hospital Information first.')
            return redirect('/hospital-admin/verification/hospital-information/')
        
        # Check if Step 2 is complete (has hospital_email)
        if not application.hospital_email:
            messages.warning(request, 'Please complete Step 2: Contact Information first.')
            return redirect('/hospital-admin/verification/contact-information/')
        
        form = HospitalAddressInformationForm(request.POST, instance=application)
        
        if form.is_valid():
            # Save the form but keep status as draft
            application = form.save(commit=False)
            application.status = 'draft'
            application.save()
            
            messages.success(request, 'Address information saved successfully!')
            
            # Determine action
            if 'save_continue' in request.POST:
                # Redirect to Step 4 - Documents (will be implemented later)
                messages.info(request, 'Step 4: Documents Upload will be available in the next update.')
                return redirect('/hospital-admin/verification/documents/')
            elif 'save_draft' in request.POST:
                messages.info(request, 'Your progress has been saved. You can continue later.')
                return redirect('hospital_admin:dashboard')
            else:
                return redirect('/hospital-admin/verification/address-information/')
        
        # Form has errors
        messages.error(request, 'Please correct the highlighted errors.')
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 3,
            'total_steps': 5,
            'progress_percentage': 60,
            'page_title': 'Address Information',
            'current_page': 'Address Information',
            'breadcrumb': 'Verification / Address Information',
        }
        return render(request, self.template_name, context)
    
    def get_or_create_application(self, user):
        """Get existing application or create a new draft."""
        application = HospitalApplication.objects.filter(
            hospital_admin=user
        ).order_by('-created_at').first()
        
        if not application:
            # Create a new draft application
            application = HospitalApplication.objects.create(
                hospital_admin=user,
                status='draft',
                hospital_name='',
                hospital_type='general',
                license_number='',
                registration_number='',
                admin_name=user.get_full_name() or user.username,
                admin_email=user.email,
                admin_phone=user.phone or '',
                terms_accepted=False,
            )
        
        return application
    

# =============================================================================
# HOSPITAL DOCUMENTS VIEW
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class HospitalVerificationDocumentsView(HospitalAdminBaseView):
    """Step 4: Documents Upload."""
    template_name = 'hospital_admin/verification/documents.html'
    
    def get(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # Check if Step 1 is complete (has hospital_name)
        if not application.hospital_name:
            messages.warning(request, 'Please complete Step 1: Hospital Information first.')
            return redirect('/hospital-admin/verification/hospital-information/')
        
        # Check if Step 2 is complete (has hospital_email)
        if not application.hospital_email:
            messages.warning(request, 'Please complete Step 2: Contact Information first.')
            return redirect('/hospital-admin/verification/contact-information/')
        
        # Check if Step 3 is complete (has division)
        if not application.division:
            messages.warning(request, 'Please complete Step 3: Address Information first.')
            return redirect('/hospital-admin/verification/address-information/')
        
        form = HospitalDocumentsForm(instance=application)
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 4,
            'total_steps': 5,
            'progress_percentage': 80,
            'page_title': 'Documents Upload',
            'current_page': 'Documents Upload',
            'breadcrumb': 'Verification / Documents Upload',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        form = HospitalDocumentsForm(request.POST, request.FILES, instance=application)
        
        if form.is_valid():
            # Save the form but keep status as draft
            application = form.save(commit=False)
            application.status = 'draft'
            application.save()
            
            messages.success(request, 'Documents uploaded successfully!')
            
            # Determine action
            if 'save_continue' in request.POST:
                # Redirect to Step 5 - Review & Submit (will be implemented later)
                messages.info(request, 'Step 5: Review & Submit will be available in the next update.')
                return redirect('/hospital-admin/verification/review/')
            elif 'save_draft' in request.POST:
                messages.info(request, 'Your progress has been saved. You can continue later.')
                return redirect('hospital_admin:dashboard')
            else:
                return redirect('/hospital-admin/verification/documents/')
        
        # Form has errors
        messages.error(request, 'Please correct the highlighted errors.')
        
        context = {
            'user': request.user,
            'application': application,
            'form': form,
            'current_step': 4,
            'total_steps': 5,
            'progress_percentage': 80,
            'page_title': 'Documents Upload',
            'current_page': 'Documents Upload',
            'breadcrumb': 'Verification / Documents Upload',
        }
        return render(request, self.template_name, context)
    
    def get_or_create_application(self, user):
        """Get existing application or create a new draft."""
        application = HospitalApplication.objects.filter(
            hospital_admin=user
        ).order_by('-created_at').first()
        
        if not application:
            # Create a new draft application
            application = HospitalApplication.objects.create(
                hospital_admin=user,
                status='draft',
                hospital_name='',
                hospital_type='general',
                license_number='',
                registration_number='',
                admin_name=user.get_full_name() or user.username,
                admin_email=user.email,
                admin_phone=user.phone or '',
                terms_accepted=False,
            )
        
        return application
    
# =============================================================================
# HOSPITAL VERIFICATION REVIEW VIEW
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class HospitalVerificationReviewView(HospitalAdminBaseView):
    """Step 5: Review & Submit."""
    template_name = 'hospital_admin/verification/review.html'
    
    def get(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # If no application, redirect to step 1
        if not application or not application.hospital_name:
            messages.warning(request, 'Please start the verification process first.')
            return redirect('/hospital-admin/verification/hospital-information/')
        
        # If application is already submitted, show submitted summary
        if application.status == 'submitted' or application.status == 'under_review':
            messages.info(request, 'Your application has already been submitted.')
            return render(request, 'hospital_admin/verification/submitted.html', {
                'application': application,
                'page_title': 'Application Submitted',
                'current_page': 'Application Submitted',
                'breadcrumb': 'Verification / Submitted',
            })
        
        # Check if all steps are complete
        missing_fields = self.check_completeness(application)
        
        context = {
            'user': request.user,
            'application': application,
            'current_step': 5,
            'total_steps': 5,
            'progress_percentage': 100,
            'missing_fields': missing_fields,
            'page_title': 'Review & Submit',
            'current_page': 'Review & Submit',
            'breadcrumb': 'Verification / Review & Submit',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Get or create application
        application = self.get_or_create_application(request.user)
        
        # If already verified, redirect to dashboard
        if self.is_verified:
            messages.info(request, 'Your hospital is already verified.')
            return redirect('hospital_admin:dashboard')
        
        # Check if application exists
        if not application or not application.hospital_name:
            messages.warning(request, 'Please start the verification process first.')
            return redirect('/hospital-admin/verification/hospital-information/')
        
        # If already submitted, show submitted page
        if application.status == 'submitted' or application.status == 'under_review':
            messages.info(request, 'Your application has already been submitted.')
            return redirect('hospital_admin:dashboard')
        
        # Validate declaration
        declaration = request.POST.get('declaration', False)
        if not declaration:
            messages.error(request, 'Please confirm that all information provided is true and accurate.')
            return redirect('/hospital-admin/verification/review/')
        
        # Check if all required fields are complete
        missing_fields = self.check_completeness(application)
        if missing_fields:
            messages.error(request, 'Please complete all required information before submitting.')
            return redirect('/hospital-admin/verification/review/')
        
        # Update application status to submitted
        application.status = 'submitted'
        application.submitted_at = timezone.now()
        application.save()
        
        messages.success(request, f'Your hospital verification request has been submitted successfully! Application Number: {application.application_number}')
        return redirect('hospital_admin:dashboard')
    
    def check_completeness(self, application):
        """Check if all required fields are complete."""
        missing = []
        
        # Check Step 1: Hospital Information
        if not application.hospital_name:
            missing.append('Hospital Name')
        if not application.hospital_type:
            missing.append('Hospital Type')
        if not application.license_number:
            missing.append('License Number')
        if not application.registration_number:
            missing.append('Registration Number')
        
        # Check Step 2: Contact Information
        if not application.hospital_email:
            missing.append('Hospital Email')
        if not application.phone:
            missing.append('Phone Number')
        
        # Check Step 3: Address Information
        if not application.division:
            missing.append('Division')
        if not application.district:
            missing.append('District')
        if not application.full_address:
            missing.append('Full Address')
        
        # Check Step 4: Documents
        if not application.trade_license:
            missing.append('Trade License')
        if not application.hospital_license:
            missing.append('Hospital License')
        
        return missing
    
    def get_or_create_application(self, user):
        """Get existing application or create a new draft."""
        application = HospitalApplication.objects.filter(
            hospital_admin=user
        ).order_by('-created_at').first()
        
        if not application:
            # Create a new draft application
            application = HospitalApplication.objects.create(
                hospital_admin=user,
                status='draft',
                hospital_name='',
                hospital_type='general',
                license_number='',
                registration_number='',
                admin_name=user.get_full_name() or user.username,
                admin_email=user.email,
                admin_phone=user.phone or '',
                terms_accepted=False,
            )
        
        return application

# =============================================================================
# DOCTOR MANAGEMENT - DASHBOARD
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DoctorDashboardView(HospitalAdminBaseView):
    """Doctor Management Dashboard."""
    template_name = 'hospital_admin/doctors/dashboard.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        # Get statistics
        from doctors.models import Doctor
        doctors = Doctor.objects.filter(hospital=hospital)
        
        total_doctors = doctors.count()
        active_doctors = doctors.filter(is_active=True).count()
        pending_verification = doctors.filter(is_verified=False).count()
        rejected_requests = doctors.filter(is_verified=False, is_active=False).count()
        
        # Recently added doctors
        recent_doctors = doctors.order_by('-created_at')[:5]
        
        context = {
            'total_doctors': total_doctors,
            'active_doctors': active_doctors,
            'pending_verification': pending_verification,
            'rejected_requests': rejected_requests,
            'recent_doctors': recent_doctors,
            'page_title': 'Doctor Dashboard',
            'current_page': 'Doctor Dashboard',
            'breadcrumb': 'Doctor Management / Dashboard',
        }
        return render(request, self.template_name, context)


# =============================================================================
# ALL DOCTORS
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AllDoctorsView(HospitalAdminBaseView):
    """List all doctors."""
    template_name = 'hospital_admin/doctors/all_doctors.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        from doctors.models import Doctor
        from hospitals.models import HospitalDepartment
        
        doctors = Doctor.objects.filter(hospital=hospital).select_related('user').prefetch_related('specialties')
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            doctors = doctors.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(registration_number__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        # Department filter
        dept_filter = request.GET.get('department', '')
        if dept_filter:
            doctors = doctors.filter(specialties__id=dept_filter).distinct()
        
        # Status filter
        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            doctors = doctors.filter(is_active=True)
        elif status_filter == 'inactive':
            doctors = doctors.filter(is_active=False)
        
        # Sort
        sort_by = request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            doctors = doctors.order_by('-created_at')
        elif sort_by == 'oldest':
            doctors = doctors.order_by('created_at')
        elif sort_by == 'name_asc':
            doctors = doctors.order_by('user__first_name')
        elif sort_by == 'name_desc':
            doctors = doctors.order_by('-user__first_name')
        
        # Pagination
        paginator = Paginator(doctors, 10)
        page = request.GET.get('page', 1)
        
        try:
            doctors_page = paginator.page(page)
        except PageNotAnInteger:
            doctors_page = paginator.page(1)
        except EmptyPage:
            doctors_page = paginator.page(paginator.num_pages)
        
        # Get departments for filter
        departments = HospitalDepartment.objects.filter(hospital=hospital, active=True)
        
        context = {
            'doctors': doctors_page,
            'total_doctors': doctors.count(),
            'departments': departments,
            'search_query': search_query,
            'dept_filter': dept_filter,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'page_title': 'All Doctors',
            'current_page': 'All Doctors',
            'breadcrumb': 'Doctor Management / All Doctors',
        }
        return render(request, self.template_name, context)


# =============================================================================
# ADD DOCTOR REQUEST
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AddDoctorRequestView(HospitalAdminBaseView):
    """Add doctor verification request."""
    template_name = 'hospital_admin/doctors/add_doctor.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        # Get submitted requests
        from doctors.models import Doctor
        hospital = request.user.hospital
        submitted_requests = Doctor.objects.filter(hospital=hospital, is_verified=False)
        
        context = {
            'submitted_requests': submitted_requests,
            'page_title': 'Add Doctor',
            'current_page': 'Add Doctor',
            'breadcrumb': 'Doctor Management / Add Doctor',
        }
        return render(request, self.template_name, context)


# =============================================================================
# DOCTOR VERIFICATION
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DoctorVerificationView(HospitalAdminBaseView):
    """Doctor verification management with tabs."""
    template_name = 'hospital_admin/doctors/doctor_verification.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        from doctors.models import Doctor
        from hospitals.models import HospitalDepartment
        
        # Get all doctors for this hospital
        all_doctors = Doctor.objects.filter(hospital=hospital).select_related('user')
        
        # Get tab from query parameter
        tab = request.GET.get('tab', 'pending')
        
        # Filter by status
        if tab == 'pending':
            doctors = all_doctors.filter(is_verified=False, is_active=True)
        elif tab == 'verified':
            doctors = all_doctors.filter(is_verified=True, is_active=True)
        elif tab == 'rejected':
            doctors = all_doctors.filter(is_verified=False, is_active=False)
        else:
            doctors = all_doctors.filter(is_verified=False, is_active=True)
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            doctors = doctors.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(registration_number__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(specialties__name__icontains=search_query)
            ).distinct()
        
        # Department filter - only verified departments
        dept_filter = request.GET.get('department', '')
        if dept_filter:
            doctors = doctors.filter(specialties__id=dept_filter).distinct()
        
        # Sort
        sort_by = request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            doctors = doctors.order_by('-created_at')
        elif sort_by == 'oldest':
            doctors = doctors.order_by('created_at')
        elif sort_by == 'name_asc':
            doctors = doctors.order_by('user__first_name')
        elif sort_by == 'name_desc':
            doctors = doctors.order_by('-user__first_name')
        elif sort_by == 'department':
            doctors = doctors.order_by('specialties__name')
        
        # Pagination
        paginator = Paginator(doctors, 10)
        page = request.GET.get('page', 1)
        
        try:
            doctors_page = paginator.page(page)
        except PageNotAnInteger:
            doctors_page = paginator.page(1)
        except EmptyPage:
            doctors_page = paginator.page(paginator.num_pages)
        
        # Get verified departments for filter
        departments = HospitalDepartment.objects.filter(
            hospital=hospital, 
            active=True
        ).order_by('name')
        
        # Get counts for badges and stats
        pending_count = all_doctors.filter(is_verified=False, is_active=True).count()
        verified_count = all_doctors.filter(is_verified=True, is_active=True).count()
        rejected_count = all_doctors.filter(is_verified=False, is_active=False).count()
        
        # Today's requests
        from django.utils import timezone
        today = timezone.now().date()
        today_requests = all_doctors.filter(created_at__date=today).count()
        
        context = {
            'doctors': doctors_page,
            'tab': tab,
            'pending_count': pending_count,
            'verified_count': verified_count,
            'rejected_count': rejected_count,
            'today_requests': today_requests,
            'departments': departments,
            'search_query': search_query,
            'dept_filter': dept_filter,
            'sort_by': sort_by,
            'page_title': 'Doctor Verification',
            'current_page': 'Doctor Verification',
            'breadcrumb': 'Doctor Management / Verification',
            'pending_doctors': pending_count,
            'verified_doctors': verified_count,
            'rejected_doctors': rejected_count,
        }
        return render(request, self.template_name, context)


# =============================================================================
# DOCTOR VERIFICATION DETAIL
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DoctorVerificationDetailView(HospitalAdminBaseView):
    """View doctor verification details."""
    template_name = 'hospital_admin/doctors/doctor_verification_detail.html'
    
    def get(self, request, doctor_id):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        from doctors.models import Doctor
        
        doctor = get_object_or_404(Doctor, id=doctor_id, hospital=request.user.hospital)
        
        context = {
            'doctor': doctor,
            'page_title': f'Verification: {doctor.user.get_full_name()}',
            'current_page': 'Verification Detail',
            'breadcrumb': 'Doctor Management / Verification / Detail',
        }
        return render(request, self.template_name, context)


# =============================================================================
# APPROVE DOCTOR VERIFICATION
# =============================================================================
import traceback

@login_required
@role_required(['hospital_admin'])
def approve_doctor(request, doctor_id):
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("hospital_admin:doctor_verification")

    try:
        doctor = get_object_or_404(
            Doctor,
            id=doctor_id,
            hospital=request.user.hospital
        )

        doctor.is_verified = True
        doctor.is_active = True
        doctor.save()

        messages.success(
            request,
            f"{doctor.user.get_full_name()} approved successfully."
        )

    except Exception as e:
        print(traceback.format_exc())   # <-- Terminal-এ পুরো error দেখাবে
        messages.error(request, str(e))

    return redirect("hospital_admin:doctor_verification")


@login_required
@role_required(['hospital_admin'])
def reject_doctor(request, doctor_id):
    """Reject a doctor verification request."""
    from doctors.models import Doctor
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:doctor_verification')
    
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=request.user.hospital)
    
    reason = request.POST.get('reason', '')
    if not reason:
        messages.error(request, 'Please provide a rejection reason.')
        return redirect('hospital_admin:pending_doctor_detail', doctor_id=doctor_id)
    
    doctor.is_verified = False
    doctor.is_active = False
    doctor.save()
    
    messages.warning(request, f'Doctor {doctor.user.get_full_name()} rejected.')
    return redirect('hospital_admin:doctor_verification')


# =============================================================================
# DEPARTMENTS
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DepartmentListView(HospitalAdminBaseView):
    """List all departments."""
    template_name = 'hospital_admin/departments/all_departments.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        from hospitals.models import HospitalDepartment
        from doctors.models import Doctor
        
        hospital = request.user.hospital
        departments = HospitalDepartment.objects.filter(hospital=hospital)
        
        # Get doctor count for each department
        for dept in departments:
            dept.doctor_count = Doctor.objects.filter(specialties__name=dept.name, is_active=True).count()

        
        context = {
            'departments': departments,
            'page_title': 'Departments',
            'current_page': 'Departments',
            'breadcrumb': 'Doctor Management / Departments',
        }
        return render(request, self.template_name, context)
    
# =============================================================================
# PENDING DOCTOR DETAIL
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class PendingDoctorDetailView(HospitalAdminBaseView):
    """View pending doctor verification details."""
    template_name = 'hospital_admin/doctors/pending_doctor_detail.html'
    
    def get(self, request, doctor_id):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        from doctors.models import Doctor
        
        doctor = get_object_or_404(Doctor, id=doctor_id, hospital=request.user.hospital)
        
        # Get verification checklist
        checklist = self.get_checklist(doctor)
        
        context = {
            'doctor': doctor,
            'checklist': checklist,
            'page_title': 'Doctor Verification Request',
            'current_page': 'Doctor Detail',
            'breadcrumb': 'Doctor Management / Doctor Verification / Doctor Detail',
        }
        return render(request, self.template_name, context)
    
    def get_checklist(self, doctor):
        """Get verification checklist status."""
        return {
            'personal_info': bool(doctor.user.get_full_name() and doctor.user.email and doctor.user.phone),
            'professional_info': bool(doctor.registration_number and doctor.qualification),
            'education': bool(doctor.qualification),
            'certificates': bool(doctor.profile_photo),
            'bmdc': bool(doctor.registration_number),
            'documents': bool(doctor.profile_photo),
        }
    
@login_required
@role_required(['hospital_admin'])
def deactivate_doctor(request, doctor_id):
    """Deactivate a verified doctor."""
    from doctors.models import Doctor
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:doctor_verification')
    
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=request.user.hospital)
    
    # Deactivate the doctor
    doctor.is_active = False
    doctor.save()
    
    messages.warning(request, f'Doctor {doctor.user.get_full_name()} has been deactivated.')
    return redirect('hospital_admin:doctor_verification?tab=verified')

# =============================================================================
# DEPARTMENT MANAGEMENT - DASHBOARD
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DepartmentDashboardView(HospitalAdminBaseView):
    """Department Management Dashboard."""
    template_name = 'hospital_admin/departments/department_dashboard.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        # Get all departments
        departments = list(HospitalDepartment.objects.filter(
            hospital=hospital
        ).order_by('name'))
        
        # Get all doctors for this hospital
        from doctors.models import Doctor
        hospital_doctors = Doctor.objects.filter(hospital=hospital, is_active=True)
        
        # For each department, count doctors with matching specialty
        for dept in departments:
            # Count doctors with this department name as a specialty
            count = hospital_doctors.filter(
                specialties__name=dept.name
            ).count()
            
            # If no doctors found, try case-insensitive match
            if count == 0:
                count = hospital_doctors.filter(
                    specialties__name__iexact=dept.name
                ).count()
            
            # If still 0, try matching by qualification text
            if count == 0:
                count = hospital_doctors.filter(
                    qualification__icontains=dept.name
                ).count()
            
            # Set the attribute on the department object
            dept.doctor_count = count
        
        # Statistics
        total_departments = len(departments)
        active_departments = sum(1 for d in departments if d.active)
        assigned_heads = sum(1 for d in departments if d.head_doctor_id is not None)
        assigned_doctors = hospital_doctors.count()
        
        # Recent activities
        recent_activities = [
            {'icon': 'fa-plus-circle', 'color': 'blue', 'text': 'Cardiology Department Created', 'time': '2 hours ago'},
            {'icon': 'fa-edit', 'color': 'yellow', 'text': 'Neurology Department Updated', 'time': '5 hours ago'},
            {'icon': 'fa-user-check', 'color': 'green', 'text': 'Orthopedic Head Assigned', 'time': '1 day ago'},
            {'icon': 'fa-bolt', 'color': 'orange', 'text': 'Emergency Department Activated', 'time': '2 days ago'},
            {'icon': 'fa-file-alt', 'color': 'purple', 'text': 'Pediatrics Information Updated', 'time': '3 days ago'},
        ]
        
        # Department distribution (top 5 by doctor count)
        dept_distribution = sorted(departments, key=lambda d: getattr(d, 'doctor_count', 0), reverse=True)[:5]
        
        # Pending tasks
        pending_tasks = [
            {'text': 'Assign Head to Dermatology', 'priority': 'high'},
            {'text': 'Review Oncology Department', 'priority': 'medium'},
            {'text': 'Update Pediatrics Information', 'priority': 'low'},
            {'text': 'Add New Department: Radiology', 'priority': 'high'},
        ]
        
        # Search and filter
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        sort_by = request.GET.get('sort', 'newest')
        
        # Apply filters
        if search_query:
            departments = [d for d in departments if search_query.lower() in d.name.lower()]
        
        if status_filter == 'active':
            departments = [d for d in departments if d.active]
        elif status_filter == 'inactive':
            departments = [d for d in departments if not d.active]
        
        if sort_by == 'newest':
            departments = sorted(departments, key=lambda d: d.created_at, reverse=True)
        elif sort_by == 'oldest':
            departments = sorted(departments, key=lambda d: d.created_at)
        elif sort_by == 'name':
            departments = sorted(departments, key=lambda d: d.name)
        
        # Debug: Print counts
        print("\n=== Department Doctor Counts ===")
        for dept in departments:
            print(f"  {dept.name}: {getattr(dept, 'doctor_count', 0)} doctors")
        
        context = {
            'departments': departments,
            'total_departments': total_departments,
            'active_departments': active_departments,
            'assigned_heads': assigned_heads,
            'assigned_doctors': assigned_doctors,
            'recent_activities': recent_activities,
            'dept_distribution': dept_distribution,
            'pending_tasks': pending_tasks,
            'search_query': search_query,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'page_title': 'Department Dashboard',
            'current_page': 'Department Dashboard',
            'breadcrumb': 'Department Management / Dashboard',
        }
        return render(request, self.template_name, context)
    
# =============================================================================
# ALL DEPARTMENTS
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AllDepartmentsView(HospitalAdminBaseView):
    """List all departments with search, filter, and pagination."""
    template_name = 'hospital_admin/departments/all_departments.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        # Get all departments
        departments = HospitalDepartment.objects.filter(
            hospital=hospital
        ).order_by('name')
        
        # Get all doctors for this hospital
        hospital_doctors = Doctor.objects.filter(hospital=hospital, is_active=True)
        
        # For each department, count doctors with matching specialty
        for dept in departments:
            # IMPORTANT: Use specialties__name=dept.name NOT specialties=dept
            dept.doctor_count = hospital_doctors.filter(
                specialties__name=dept.name
            ).count()
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            departments = departments.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Status filter
        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            departments = departments.filter(active=True)
        elif status_filter == 'inactive':
            departments = departments.filter(active=False)
        
        # Sort
        sort_by = request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            departments = departments.order_by('-created_at')
        elif sort_by == 'oldest':
            departments = departments.order_by('created_at')
        elif sort_by == 'name_asc':
            departments = departments.order_by('name')
        elif sort_by == 'name_desc':
            departments = departments.order_by('-name')
        
        # Re-calculate doctor counts after filtering
        for dept in departments:
            dept.doctor_count = hospital_doctors.filter(
                specialties__name=dept.name
            ).count()
        
        # Statistics
        total_departments = HospitalDepartment.objects.filter(hospital=hospital).count()
        active_departments = HospitalDepartment.objects.filter(hospital=hospital, active=True).count()
        inactive_departments = HospitalDepartment.objects.filter(hospital=hospital, active=False).count()
        total_doctors = hospital_doctors.count()
        
        # Pagination
        paginator = Paginator(departments, 10)
        page = request.GET.get('page', 1)
        
        try:
            departments_page = paginator.page(page)
        except PageNotAnInteger:
            departments_page = paginator.page(1)
        except EmptyPage:
            departments_page = paginator.page(paginator.num_pages)
        
        context = {
            'departments': departments_page,
            'total_departments': total_departments,
            'active_departments': active_departments,
            'inactive_departments': inactive_departments,
            'total_doctors': total_doctors,
            'search_query': search_query,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'page_title': 'All Departments',
            'current_page': 'All Departments',
            'breadcrumb': 'Department Management / All Departments',
        }
        return render(request, self.template_name, context)



# =============================================================================
# DEPARTMENT DETAIL VIEW
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DepartmentDetailView(HospitalAdminBaseView):
    """View department details."""
    template_name = 'hospital_admin/departments/department_detail.html'
    
    def get(self, request, department_id):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        # Get the department
        department = get_object_or_404(HospitalDepartment, id=department_id, hospital=hospital)
        
        # Get doctors in this department (with matching specialty)
        from doctors.models import Doctor
        doctors = Doctor.objects.filter(
            hospital=hospital,
            specialties__name=department.name,
            is_active=True
        ).select_related('user').prefetch_related('specialties')
        
        # Statistics
        total_doctors = doctors.count()
        available_doctors = doctors.filter(is_verified=True).count()
        
        # Get facilities from department (you can add these fields to the model or use default)
        facilities = {
            'emergency_service': True,
            'icu': True,
            'operation_theater': False,
            'laboratory': True,
            'pharmacy': True,
            'waiting_area': True,
            'reception': True,
            'wheelchair_accessible': True,
            'twenty_four_hours': False,
        }
        
        # Recent activities (simulated)
        recent_activities = [
            {'icon': 'fa-user-plus', 'color': 'green', 'text': 'Dr. John Doe assigned to department', 'time': '2 hours ago'},
            {'icon': 'fa-edit', 'color': 'blue', 'text': 'Department information updated', 'time': '5 hours ago'},
            {'icon': 'fa-user-tie', 'color': 'purple', 'text': 'Department Head changed to Dr. Jane Smith', 'time': '1 day ago'},
            {'icon': 'fa-clock', 'color': 'yellow', 'text': 'Working hours updated', 'time': '2 days ago'},
        ]
        
        context = {
            'department': department,
            'doctors': doctors,
            'total_doctors': total_doctors,
            'available_doctors': available_doctors,
            'total_patients': 0,  # Add your patient count logic here
            'today_appointments': 0,  # Add your appointment count logic here
            'facilities': facilities,
            'recent_activities': recent_activities,
            'page_title': department.name,
            'current_page': 'Department Detail',
            'breadcrumb': f'Department Management / {department.name}',
        }
        return render(request, self.template_name, context)


# =============================================================================
# TOGGLE DEPARTMENT STATUS
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def toggle_department_status(request, department_id):
    """Toggle department active status."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:all_departments')
    
    department = get_object_or_404(
        HospitalDepartment, 
        id=department_id, 
        hospital=request.user.hospital
    )
    
    department.active = not department.active
    department.save()
    
    status = 'activated' if department.active else 'deactivated'
    messages.success(request, f'Department "{department.name}" has been {status}.')
    
    return redirect('hospital_admin:all_departments')


# =============================================================================
# DELETE DEPARTMENT
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def delete_department(request, department_id):
    """Delete a department."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:all_departments')
    
    department = get_object_or_404(
        HospitalDepartment, 
        id=department_id, 
        hospital=request.user.hospital
    )
    
    department_name = department.name
    department.delete()
    
    messages.success(request, f'Department "{department_name}" has been deleted.')
    
    return redirect('hospital_admin:all_departments')

@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AddDepartmentView(HospitalAdminBaseView):
    """Add a new department."""
    template_name = 'hospital_admin/departments/add_department.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        form = DepartmentForm(hospital=hospital)
        
        context = {
            'form': form,
            'page_title': 'Add Department',
            'current_page': 'Add Department',
            'breadcrumb': 'Department Management / Add Department',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        form = DepartmentForm(request.POST, hospital=hospital)
        
        if form.is_valid():
            department = form.save(commit=False)
            department.hospital = hospital
            department.created_by = request.user
            department.save()
            
            messages.success(request, f'Department "{department.name}" created successfully!')
            
            if 'save_another' in request.POST:
                return redirect('hospital_admin:add_department')
            else:
                return redirect('hospital_admin:all_departments')
        
        context = {
            'form': form,
            'page_title': 'Add Department',
            'current_page': 'Add Department',
            'breadcrumb': 'Department Management / Add Department',
        }
        return render(request, self.template_name, context)
    
# =============================================================================
# EDIT DEPARTMENT
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class EditDepartmentView(HospitalAdminBaseView):
    """Edit department details."""
    template_name = 'hospital_admin/departments/edit_department.html'
    
    def get(self, request, department_id):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        department = get_object_or_404(HospitalDepartment, id=department_id, hospital=hospital)
        
        # Get verified doctors for the dropdown
        from doctors.models import Doctor
        verified_doctors = Doctor.objects.filter(
            hospital=hospital,
            is_verified=True,
            is_active=True
        ).select_related('user')
        
        form = EditDepartmentForm(instance=department, hospital=hospital)
        
        context = {
            'department': department,
            'form': form,
            'verified_doctors': verified_doctors,
            'page_title': 'Edit Department',
            'current_page': 'Edit Department',
            'breadcrumb': f'Department Management / {department.name} / Edit',
        }
        return render(request, self.template_name, context)
    
    def post(self, request, department_id):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        department = get_object_or_404(HospitalDepartment, id=department_id, hospital=hospital)
        
        form = EditDepartmentForm(request.POST, instance=department, hospital=hospital)
        
        if form.is_valid():
            department = form.save(commit=False)
            department.updated_by = request.user
            department.save()
            
            messages.success(request, f'Department "{department.name}" updated successfully!')
            
            if 'save_continue' in request.POST:
                return redirect('hospital_admin:edit_department', department_id=department.id)
            else:
                return redirect('hospital_admin:all_departments')
        
        # Form has errors
        context = {
            'department': department,
            'form': form,
            'page_title': 'Edit Department',
            'current_page': 'Edit Department',
            'breadcrumb': f'Department Management / {department.name} / Edit',
        }
        return render(request, self.template_name, context)
    
# =============================================================================
# DEPARTMENT HEADS MANAGEMENT
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DepartmentHeadsView(HospitalAdminBaseView):
    """Manage department heads."""
    template_name = 'hospital_admin/departments/department_heads.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        from doctors.models import Doctor
        from hospitals.models import HospitalDepartment
        
        # Get all departments
        departments = HospitalDepartment.objects.filter(
            hospital=hospital
        ).order_by('name')
        
        # Get verified doctors
        verified_doctors = Doctor.objects.filter(
            hospital=hospital,
            is_verified=True,
            is_active=True
        ).select_related('user')
        
        # Statistics
        total_departments = departments.count()
        assigned_heads = departments.filter(head_doctor__isnull=False).count()
        unassigned_departments = departments.filter(head_doctor__isnull=True).count()
        available_doctors = verified_doctors.count()
        
        # Search and filters
        search_query = request.GET.get('search', '')
        status_filter = request.GET.get('status', '')
        sort_by = request.GET.get('sort', 'name')
        
        # Apply search
        if search_query:
            departments = departments.filter(
                Q(name__icontains=search_query) |
                Q(head_doctor__user__first_name__icontains=search_query) |
                Q(head_doctor__user__last_name__icontains=search_query)
            )
        
        # Apply status filter
        if status_filter == 'assigned':
            departments = departments.filter(head_doctor__isnull=False)
        elif status_filter == 'unassigned':
            departments = departments.filter(head_doctor__isnull=True)
        
        # Apply sort
        if sort_by == 'name':
            departments = departments.order_by('name')
        elif sort_by == 'newest':
            departments = departments.order_by('-created_at')
        elif sort_by == 'oldest':
            departments = departments.order_by('created_at')
        
        # Pagination
        paginator = Paginator(departments, 10)
        page = request.GET.get('page', 1)
        
        try:
            departments_page = paginator.page(page)
        except PageNotAnInteger:
            departments_page = paginator.page(1)
        except EmptyPage:
            departments_page = paginator.page(paginator.num_pages)
        
        context = {
            'departments': departments_page,
            'total_departments': total_departments,
            'assigned_heads': assigned_heads,
            'unassigned_departments': unassigned_departments,
            'available_doctors': available_doctors,
            'verified_doctors': verified_doctors,
            'search_query': search_query,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'page_title': 'Department Heads',
            'current_page': 'Department Heads',
            'breadcrumb': 'Department Management / Department Heads',
        }
        return render(request, self.template_name, context)


# =============================================================================
# ASSIGN DEPARTMENT HEAD
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def assign_department_head(request):
    """Assign a doctor as department head."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:department_heads')
    
    department_id = request.POST.get('department_id')
    doctor_id = request.POST.get('doctor_id')
    
    if not department_id or not doctor_id:
        messages.error(request, 'Please select both department and doctor.')
        return redirect('hospital_admin:department_heads')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    from doctors.models import Doctor
    from hospitals.models import HospitalDepartment
    
    # Get department
    department = get_object_or_404(HospitalDepartment, id=department_id, hospital=hospital)
    
    # Get doctor
    doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)
    
    # Check if doctor is verified and active
    if not doctor.is_verified or not doctor.is_active:
        messages.error(request, 'Doctor must be verified and active.')
        return redirect('hospital_admin:department_heads')
    
    # Check if doctor is already head of another department
    existing_head = HospitalDepartment.objects.filter(
        hospital=hospital,
        head_doctor=doctor
    ).exclude(id=department.id).first()
    
    if existing_head:
        messages.error(request, f'Dr. {doctor.user.get_full_name()} is already the head of "{existing_head.name}".')
        return redirect('hospital_admin:department_heads')
    
    # Assign head
    department.head_doctor = doctor
    department.save()
    
    messages.success(request, f'Dr. {doctor.user.get_full_name()} assigned as head of "{department.name}".')
    return redirect('hospital_admin:department_heads')


# =============================================================================
# CHANGE DEPARTMENT HEAD
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def change_department_head(request, department_id):
    """Change department head."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:department_heads')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    from doctors.models import Doctor
    from hospitals.models import HospitalDepartment
    
    department = get_object_or_404(HospitalDepartment, id=department_id, hospital=hospital)
    
    new_doctor_id = request.POST.get('new_doctor_id')
    if not new_doctor_id:
        messages.error(request, 'Please select a new doctor.')
        return redirect('hospital_admin:department_heads')
    
    new_doctor = get_object_or_404(Doctor, id=new_doctor_id, hospital=hospital)
    
    # Check if doctor is verified and active
    if not new_doctor.is_verified or not new_doctor.is_active:
        messages.error(request, 'Doctor must be verified and active.')
        return redirect('hospital_admin:department_heads')
    
    # Check if doctor is already head of another department
    existing_head = HospitalDepartment.objects.filter(
        hospital=hospital,
        head_doctor=new_doctor
    ).exclude(id=department.id).first()
    
    if existing_head:
        messages.error(request, f'Dr. {new_doctor.user.get_full_name()} is already the head of "{existing_head.name}".')
        return redirect('hospital_admin:department_heads')
    
    # Remove old head and assign new
    department.head_doctor = new_doctor
    department.save()
    
    messages.success(request, f'Department head changed to Dr. {new_doctor.user.get_full_name()}.')
    return redirect('hospital_admin:department_heads')


# =============================================================================
# REMOVE DEPARTMENT HEAD
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def remove_department_head(request, department_id):
    """Remove department head."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:department_heads')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    from hospitals.models import HospitalDepartment
    
    department = get_object_or_404(HospitalDepartment, id=department_id, hospital=hospital)
    
    if not department.head_doctor:
        messages.warning(request, f'"{department.name}" already has no head assigned.')
        return redirect('hospital_admin:department_heads')
    
    department.head_doctor = None
    department.save()
    
    messages.success(request, f'Department head removed from "{department.name}".')
    return redirect('hospital_admin:department_heads')


# =============================================================================
# GET AVAILABLE DOCTORS API
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def get_available_doctors(request):
    """API endpoint to get available doctors for department head assignment."""
    from doctors.models import Doctor
    from hospitals.models import HospitalDepartment
    
    hospital = request.user.hospital
    if not hospital:
        return JsonResponse({'error': 'No hospital associated'}, status=403)
    
    department_id = request.GET.get('department_id')
    
    # Get all verified active doctors
    doctors = Doctor.objects.filter(
        hospital=hospital,
        is_verified=True,
        is_active=True
    ).select_related('user')
    
    # Exclude doctors who are already heads of other departments
    if department_id:
        existing_heads = HospitalDepartment.objects.filter(
            hospital=hospital,
            head_doctor__isnull=False
        ).exclude(id=department_id).values_list('head_doctor_id', flat=True)
        doctors = doctors.exclude(id__in=existing_heads)
    else:
        existing_heads = HospitalDepartment.objects.filter(
            hospital=hospital,
            head_doctor__isnull=False
        ).values_list('head_doctor_id', flat=True)
        doctors = doctors.exclude(id__in=existing_heads)
    
    data = []
    for doctor in doctors:
        data.append({
            'id': doctor.id,
            'name': f"Dr. {doctor.user.get_full_name() or doctor.user.username}",
            'specialization': doctor.specialties.first.name if doctor.specialties.exists() else 'General',
            'experience': doctor.experience or 0,
        })
    
    return JsonResponse({'doctors': data})

# =============================================================================
# ROOMS & UNITS MANAGEMENT
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class RoomsAndUnitsView(HospitalAdminBaseView):
    """Manage rooms and units."""
    template_name = 'hospital_admin/departments/rooms.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        # Get all rooms
        rooms = Room.objects.filter(hospital=hospital).select_related('department')
        
        # Statistics
        total_rooms = rooms.count()
        available_rooms = rooms.filter(status='available').count()
        occupied_rooms = rooms.filter(status='occupied').count()
        icu_rooms = rooms.filter(room_type__in=['icu', 'nicu', 'ccu']).count()
        ot_rooms = rooms.filter(room_type='operation_theater').count()
        wards = rooms.filter(room_type='general_ward').count()
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            rooms = rooms.filter(
                Q(room_number__icontains=search_query) |
                Q(department__name__icontains=search_query) |
                Q(room_type__icontains=search_query)
            )
        
        # Department filter
        dept_filter = request.GET.get('department', '')
        if dept_filter:
            rooms = rooms.filter(department_id=dept_filter)
        
        # Room type filter
        type_filter = request.GET.get('room_type', '')
        if type_filter:
            rooms = rooms.filter(room_type=type_filter)
        
        # Status filter
        status_filter = request.GET.get('status', '')
        if status_filter:
            rooms = rooms.filter(status=status_filter)
        
        # Pagination
        paginator = Paginator(rooms, 10)
        page = request.GET.get('page', 1)
        
        try:
            rooms_page = paginator.page(page)
        except PageNotAnInteger:
            rooms_page = paginator.page(1)
        except EmptyPage:
            rooms_page = paginator.page(paginator.num_pages)
        
        # Get departments for filter
        departments = HospitalDepartment.objects.filter(hospital=hospital, active=True)
        
        context = {
            'rooms': rooms_page,
            'total_rooms': total_rooms,
            'available_rooms': available_rooms,
            'occupied_rooms': occupied_rooms,
            'icu_rooms': icu_rooms,
            'ot_rooms': ot_rooms,
            'wards': wards,
            'departments': departments,
            'search_query': search_query,
            'dept_filter': dept_filter,
            'type_filter': type_filter,
            'status_filter': status_filter,
            'page_title': 'Rooms & Units',
            'current_page': 'Rooms & Units',
            'breadcrumb': 'Department Management / Rooms & Units',
        }
        return render(request, self.template_name, context)


# =============================================================================
# ADD ROOM
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def add_room(request):
    """Add a new room."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:rooms')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    form = RoomForm(request.POST, hospital=hospital)
    
    if form.is_valid():
        room = form.save(commit=False)
        room.hospital = hospital
        room.created_by = request.user
        room.save()
        
        messages.success(request, f'Room "{room.room_number}" created successfully!')
        return redirect('hospital_admin:rooms')
    
    # If form has errors, return to rooms page with errors
    messages.error(request, 'Please correct the errors below.')
    return redirect('hospital_admin:rooms')


# =============================================================================
# EDIT ROOM
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def edit_room(request, room_id):
    """Edit a room."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:rooms')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    room = get_object_or_404(Room, id=room_id, hospital=hospital)
    
    form = RoomForm(request.POST, instance=room, hospital=hospital)
    
    if form.is_valid():
        room = form.save()
        room.updated_by = request.user
        room.save()
        
        messages.success(request, f'Room "{room.room_number}" updated successfully!')
        return redirect('hospital_admin:rooms')
    
    messages.error(request, 'Please correct the errors below.')
    return redirect('hospital_admin:rooms')


# =============================================================================
# DELETE ROOM
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def delete_room(request, room_id):
    """Delete a room."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:rooms')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    room = get_object_or_404(Room, id=room_id, hospital=hospital)
    room_number = room.room_number
    room.delete()
    
    messages.success(request, f'Room "{room_number}" deleted successfully!')
    return redirect('hospital_admin:rooms')


# =============================================================================
# ROOM DETAIL
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def room_detail(request, room_id):
    """View room details."""
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    room = get_object_or_404(Room, id=room_id, hospital=hospital)
    
    context = {
        'room': room,
        'page_title': f'Room {room.room_number}',
        'current_page': 'Room Detail',
        'breadcrumb': f'Department Management / Rooms & Units / {room.room_number}',
    }
    return render(request, 'hospital_admin/departments/room_detail.html', context)


# =============================================================================
# TOGGLE ROOM STATUS
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def toggle_room_status(request, room_id):
    """Toggle room status."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    hospital = request.user.hospital
    if not hospital:
        return JsonResponse({'error': 'No hospital associated'}, status=403)
    
    room = get_object_or_404(Room, id=room_id, hospital=hospital)
    
    data = json.loads(request.body) if request.body else {}
    new_status = data.get('status')
    
    if new_status not in ['available', 'occupied', 'maintenance', 'inactive']:
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    room.status = new_status
    room.save()
    
    return JsonResponse({'success': True, 'status': new_status})

# =============================================================================
# APPOINTMENT MANAGEMENT - DASHBOARD
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AppointmentDashboardView(HospitalAdminBaseView):
    """Appointment Management Dashboard."""
    template_name = 'hospital_admin/appointments/dashboard.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        # Get all appointments for this hospital
        today = timezone.now().date()
        appointments = Appointment.objects.filter(
            hospital=hospital
        ).select_related('patient', 'doctor', 'doctor__user', 'patient__user')
        
        # Today's appointments
        today_appointments = appointments.filter(appointment_date=today)
        
        # Statistics
        today_total = today_appointments.count()
        pending_total = today_appointments.filter(status='pending').count()
        confirmed_total = today_appointments.filter(status='confirmed').count()
        completed_total = today_appointments.filter(status='completed').count()
        cancelled_total = today_appointments.filter(status='cancelled').count()
        total_appointments = appointments.count()
        
        # Recent appointments (last 10)
        recent_appointments = appointments.order_by('-created_at')[:10]
        
        # Upcoming appointments (next 10)
        upcoming_appointments = appointments.filter(
            appointment_date__gte=today,
            status__in=['pending', 'confirmed']
        ).order_by('appointment_date', 'appointment_time')[:10]
        
        # Department wise appointments - FIXED
        from hospitals.models import HospitalDepartment
        from doctors.models import Doctor
        
        departments = HospitalDepartment.objects.filter(hospital=hospital, active=True)
        dept_appointments = []
        total_count = appointments.count() or 1
        
        for dept in departments:
            # Count appointments where doctor is in this department
            # Use specialties__name to match department name
            count = appointments.filter(
                doctor__specialties__name=dept.name
            ).count()
            if count > 0:
                dept_appointments.append({
                    'name': dept.name,
                    'count': count,
                    'total': total_count
                })
        
        # Sort by count descending
        dept_appointments.sort(key=lambda x: x['count'], reverse=True)
        
        # Top busy doctors today
        top_doctors = today_appointments.values(
            'doctor__id', 
            'doctor__user__first_name', 
            'doctor__user__last_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Recent activities (simulated)
        recent_activities = [
            {'icon': 'fa-plus-circle', 'color': 'blue', 'text': 'New appointment created for Dr. Smith', 'time': '5 minutes ago'},
            {'icon': 'fa-check-circle', 'color': 'green', 'text': 'Appointment confirmed for John Doe', 'time': '15 minutes ago'},
            {'icon': 'fa-times-circle', 'color': 'red', 'text': 'Appointment cancelled by patient', 'time': '30 minutes ago'},
            {'icon': 'fa-edit', 'color': 'yellow', 'text': 'Doctor schedule updated for Cardiology', 'time': '1 hour ago'},
            {'icon': 'fa-calendar-check', 'color': 'purple', 'text': 'New appointment slot added', 'time': '2 hours ago'},
        ]
        
        context = {
            'today_total': today_total,
            'pending_total': pending_total,
            'confirmed_total': confirmed_total,
            'completed_total': completed_total,
            'cancelled_total': cancelled_total,
            'total_appointments': total_appointments,
            'recent_appointments': recent_appointments,
            'upcoming_appointments': upcoming_appointments,
            'dept_appointments': dept_appointments,
            'top_doctors': top_doctors,
            'recent_activities': recent_activities,
            'today_date': today,
            'page_title': 'Appointment Dashboard',
            'current_page': 'Appointment Dashboard',
            'breadcrumb': 'Appointment Management / Dashboard',
        }
        return render(request, self.template_name, context)


# =============================================================================
# APPOINTMENT LIST
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AppointmentListView(HospitalAdminBaseView):
    """List all appointments with search and filters."""
    template_name = 'hospital_admin/appointments/appointment_list.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        appointments = Appointment.objects.filter(
            hospital=hospital
        ).select_related('patient', 'doctor', 'doctor__user', 'patient__user')
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            appointments = appointments.filter(
                Q(patient__user__first_name__icontains=search_query) |
                Q(patient__user__last_name__icontains=search_query) |
                Q(doctor__user__first_name__icontains=search_query) |
                Q(doctor__user__last_name__icontains=search_query) |
                Q(token__icontains=search_query)
            )
        
        # Status filter
        status_filter = request.GET.get('status', '')
        if status_filter:
            appointments = appointments.filter(status=status_filter)
        
        # Date filter
        date_filter = request.GET.get('date', '')
        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                appointments = appointments.filter(appointment_date=date_obj)
            except ValueError:
                pass
        
        # Sort
        sort_by = request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            appointments = appointments.order_by('-created_at')
        elif sort_by == 'oldest':
            appointments = appointments.order_by('created_at')
        elif sort_by == 'date_asc':
            appointments = appointments.order_by('appointment_date', 'appointment_time')
        elif sort_by == 'date_desc':
            appointments = appointments.order_by('-appointment_date', '-appointment_time')
        
        # Pagination
        paginator = Paginator(appointments, 15)
        page = request.GET.get('page', 1)
        
        try:
            appointments_page = paginator.page(page)
        except PageNotAnInteger:
            appointments_page = paginator.page(1)
        except EmptyPage:
            appointments_page = paginator.page(paginator.num_pages)
        
        # Get status counts
        status_counts = {
            'pending': appointments.filter(status='pending').count(),
            'confirmed': appointments.filter(status='confirmed').count(),
            'completed': appointments.filter(status='completed').count(),
            'cancelled': appointments.filter(status='cancelled').count(),
        }
        
        context = {
            'appointments': appointments_page,
            'search_query': search_query,
            'status_filter': status_filter,
            'date_filter': date_filter,
            'sort_by': sort_by,
            'status_counts': status_counts,
            'page_title': 'All Appointments',
            'current_page': 'All Appointments',
            'breadcrumb': 'Appointment Management / All Appointments',
        }
        return render(request, self.template_name, context)


# =============================================================================
# APPOINTMENT DETAIL
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AppointmentDetailView(HospitalAdminBaseView):
    """View appointment details."""
    template_name = 'hospital_admin/appointments/appointment_detail.html'
    
    def get(self, request, appointment_id):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        appointment = get_object_or_404(
            Appointment, 
            id=appointment_id, 
            hospital=hospital
        )
        
        context = {
            'appointment': appointment,
            'page_title': f'Appointment #{appointment.id}',
            'current_page': 'Appointment Detail',
            'breadcrumb': f'Appointment Management / Appointment #{appointment.id}',
        }
        return render(request, self.template_name, context)
    
# =============================================================================
# ALL APPOINTMENTS
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AppointmentListView(HospitalAdminBaseView):
    """List all appointments with search, filter, and pagination."""
    template_name = 'hospital_admin/appointments/all_appointments.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        from appointments.models import Appointment
        from doctors.models import Doctor
        from hospitals.models import HospitalDepartment
        
        # Get all appointments for this hospital
        appointments = Appointment.objects.filter(
            hospital=hospital
        ).select_related(
            'patient', 
            'doctor', 
            'doctor__user', 
            'patient__user'
        ).prefetch_related(
            'doctor__specialties'
        )
        
        # Today's date for statistics
        today = timezone.now().date()
        
        # Statistics
        today_count = appointments.filter(appointment_date=today).count()
        pending_count = appointments.filter(status='pending').count()
        confirmed_count = appointments.filter(status='confirmed').count()
        completed_count = appointments.filter(status='completed').count()
        cancelled_count = appointments.filter(status='cancelled').count()
        total_count = appointments.count()
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            appointments = appointments.filter(
                Q(id__icontains=search_query) |
                Q(patient__user__first_name__icontains=search_query) |
                Q(patient__user__last_name__icontains=search_query) |
                Q(doctor__user__first_name__icontains=search_query) |
                Q(doctor__user__last_name__icontains=search_query) |
                Q(token__icontains=search_query)
            )
        
        # Doctor filter
        doctor_filter = request.GET.get('doctor', '')
        if doctor_filter:
            appointments = appointments.filter(doctor_id=doctor_filter)
        
        # Department filter (using doctor__specialties)
        department_filter = request.GET.get('department', '')
        if department_filter:
            appointments = appointments.filter(
                doctor__specialties__id=department_filter
            ).distinct()
        
        # Status filter
        status_filter = request.GET.get('status', '')
        if status_filter:
            appointments = appointments.filter(status=status_filter)
        
        # Date filter
        selected_date = request.GET.get('date', '')
        if selected_date:
            try:
                date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                appointments = appointments.filter(appointment_date=date_obj)
            except ValueError:
                pass
        
        # Sort
        sort_by = request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            appointments = appointments.order_by('-created_at')
        elif sort_by == 'oldest':
            appointments = appointments.order_by('created_at')
        elif sort_by == 'today':
            appointments = appointments.filter(appointment_date=today).order_by('appointment_time')
        elif sort_by == 'tomorrow':
            tomorrow = today + timedelta(days=1)
            appointments = appointments.filter(appointment_date=tomorrow).order_by('appointment_time')
        
        # Pagination
        paginator = Paginator(appointments, 15)
        page = request.GET.get('page', 1)
        
        try:
            appointments_page = paginator.page(page)
        except PageNotAnInteger:
            appointments_page = paginator.page(1)
        except EmptyPage:
            appointments_page = paginator.page(paginator.num_pages)
        
        # Get doctors and departments for filters
        doctors = Doctor.objects.filter(
            hospital=hospital,
            is_active=True
        ).select_related('user')
        
        departments = HospitalDepartment.objects.filter(
            hospital=hospital,
            active=True
        ).order_by('name')
        
        context = {
            'appointments': appointments_page,
            'today_count': today_count,
            'pending_count': pending_count,
            'confirmed_count': confirmed_count,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'total_count': total_count,
            'doctors': doctors,
            'departments': departments,
            'search_query': search_query,
            'doctor_filter': doctor_filter,
            'department_filter': department_filter,
            'status_filter': status_filter,
            'selected_date': selected_date,
            'sort_by': sort_by,
            'page_title': 'All Appointments',
            'current_page': 'All Appointments',
            'breadcrumb': 'Appointment Management / All Appointments',
        }
        return render(request, self.template_name, context)
    
@login_required
@role_required(['hospital_admin'])
def approve_appointment(request, appointment_id):
    """Approve a pending appointment."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:appointments')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    appointment = get_object_or_404(Appointment, id=appointment_id, hospital=hospital)
    
    if appointment.status != 'pending':
        messages.error(request, 'Only pending appointments can be approved.')
        return redirect('hospital_admin:appointments')
    
    appointment.status = 'confirmed'
    appointment.confirmed_at = timezone.now()
    appointment.confirmed_by = request.user
    appointment.save()
    
    messages.success(request, f'Appointment #{appointment.id} has been approved.')
    return redirect('hospital_admin:appointments')


# =============================================================================
# REJECT APPOINTMENT
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def reject_appointment(request, appointment_id):
    """Reject a pending appointment."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:appointments')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    appointment = get_object_or_404(Appointment, id=appointment_id, hospital=hospital)
    
    if appointment.status != 'pending':
        messages.error(request, 'Only pending appointments can be rejected.')
        return redirect('hospital_admin:appointments')
    
    reason = request.POST.get('rejection_reason', '').strip()
    if not reason:
        messages.error(request, 'Please provide a rejection reason.')
        return redirect('hospital_admin:appointments')
    
    appointment.status = 'cancelled'
    appointment.cancelled_at = timezone.now()
    appointment.cancelled_by = request.user
    appointment.cancellation_reason = reason
    appointment.save()
    
    messages.warning(request, f'Appointment #{appointment.id} has been rejected.')
    return redirect('hospital_admin:appointments')


# =============================================================================
# CANCEL APPOINTMENT
# =============================================================================
@login_required
@role_required(['hospital_admin'])
def cancel_appointment(request, appointment_id):
    """Cancel a confirmed appointment."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('hospital_admin:appointments')
    
    hospital = request.user.hospital
    if not hospital:
        messages.error(request, 'No hospital associated with your account.')
        return redirect('hospital_admin:dashboard')
    
    appointment = get_object_or_404(Appointment, id=appointment_id, hospital=hospital)
    
    if appointment.status not in ['pending', 'confirmed']:
        messages.error(request, 'Only pending or confirmed appointments can be cancelled.')
        return redirect('hospital_admin:appointments')
    
    note = request.POST.get('cancellation_note', '').strip()
    
    appointment.status = 'cancelled'
    appointment.cancelled_at = timezone.now()
    appointment.cancelled_by = request.user
    appointment.cancellation_note = note
    appointment.save()
    
    messages.warning(request, f'Appointment #{appointment.id} has been cancelled.')
    return redirect('hospital_admin:appointments')

# =============================================================================
# APPOINTMENT CALENDAR
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class AppointmentCalendarView(HospitalAdminBaseView):
    """Appointment Calendar view."""
    template_name = 'hospital_admin/appointments/calendar.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        from appointments.models import Appointment
        from doctors.models import Doctor
        from hospitals.models import HospitalDepartment
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        today = timezone.now().date()
        current_month = today.month
        current_year = today.year
        
        # Get all appointments for this hospital
        appointments = Appointment.objects.filter(
            hospital=hospital
        ).select_related('patient', 'doctor', 'doctor__user', 'patient__user')
        
        # Statistics
        today_count = appointments.filter(appointment_date=today).count()
        upcoming_count = appointments.filter(
            appointment_date__gte=today,
            status__in=['pending', 'confirmed']
        ).count()
        pending_count = appointments.filter(status='pending').count()
        approved_count = appointments.filter(status='confirmed').count()
        completed_count = appointments.filter(status='completed').count()
        cancelled_count = appointments.filter(status='cancelled').count()
        
        # Get all appointments as JSON for calendar
        calendar_events = []
        for appt in appointments:
            color_map = {
                'pending': '#f59e0b',
                'confirmed': '#22c55e',
                'completed': '#6366f1',
                'cancelled': '#ef4444'
            }
            
            # Get department name safely
            department_name = 'General'
            try:
                specialties = appt.doctor.specialties.all()
                if specialties.exists():
                    department_name = specialties.first().name
            except:
                department_name = 'General'
            
            calendar_events.append({
                'id': appt.id,
                'title': f"{appt.patient.user.get_full_name() or appt.patient.user.username} - Dr. {appt.doctor.user.get_full_name() or appt.doctor.user.username}",
                'start': f"{appt.appointment_date}T{appt.appointment_time}",
                'end': f"{appt.appointment_date}T{(datetime.combine(datetime.min, appt.appointment_time) + timedelta(minutes=30)).time()}",
                'color': color_map.get(appt.status, '#6b7280'),
                'status': appt.status,
                'patient': appt.patient.user.get_full_name() or appt.patient.user.username,
                'doctor': f"Dr. {appt.doctor.user.get_full_name() or appt.doctor.user.username}",
                'department': department_name,
                'time': appt.appointment_time.strftime('%I:%M %p'),
                'reason': appt.reason or 'No reason provided',
            })
        
        # Get doctors and departments for filters
        doctors = Doctor.objects.filter(
            hospital=hospital,
            is_active=True
        ).select_related('user')
        
        departments = HospitalDepartment.objects.filter(
            hospital=hospital,
            active=True
        ).order_by('name')
        
        context = {
            'appointments': appointments,
            'calendar_events': calendar_events,
            'today_count': today_count,
            'upcoming_count': upcoming_count,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'doctors': doctors,
            'departments': departments,
            'current_month': current_month,
            'current_year': current_year,
            'today': today,
            'page_title': 'Appointment Calendar',
            'current_page': 'Appointment Calendar',
            'breadcrumb': 'Appointment Management / Appointment Calendar',
        }
        return render(request, self.template_name, context)
    
# =============================================================================
# DOCTOR SCHEDULE
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class DoctorScheduleView(HospitalAdminBaseView):
    """Doctor Schedule view."""
    template_name = 'hospital_admin/appointments/doctor_schedule.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        hospital = request.user.hospital
        if not hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('hospital_admin:dashboard')
        
        from doctors.models import Doctor
        from appointments.models import Appointment
        from hospitals.models import HospitalDepartment
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        today = timezone.now().date()
        current_time = timezone.now().time()
        
        # Get all doctors for this hospital
        doctors = Doctor.objects.filter(
            hospital=hospital,
            is_active=True
        ).select_related('user').prefetch_related('specialties')
        
        # Get today's appointments
        today_appointments = Appointment.objects.filter(
            hospital=hospital,
            appointment_date=today
        ).select_related('patient', 'doctor', 'doctor__user', 'patient__user')
        
        # Statistics
        total_doctors = doctors.count()
        doctors_on_duty = doctors.filter(is_verified=True).count()
        available_doctors = doctors.filter(is_active=True, is_verified=True).count()
        
        # Count busy doctors (those with appointments today)
        busy_doctor_ids = today_appointments.values_list('doctor_id', flat=True).distinct()
        busy_doctors = busy_doctor_ids.count()
        
        today_count = today_appointments.count()
        upcoming_count = Appointment.objects.filter(
            hospital=hospital,
            appointment_date__gte=today,
            status__in=['pending', 'confirmed']
        ).count()
        
        # Get all appointments for weekly calendar
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_appointments = Appointment.objects.filter(
            hospital=hospital,
            appointment_date__gte=week_start,
            appointment_date__lte=week_end
        ).select_related('patient', 'doctor', 'doctor__user')
        
        # Build weekly schedule data
        weekly_schedule = {}
        for doctor in doctors:
            doctor_schedule = {}
            for day_offset in range(7):
                day_date = week_start + timedelta(days=day_offset)
                day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_offset]
                day_appointments = week_appointments.filter(
                    doctor=doctor,
                    appointment_date=day_date
                )
                doctor_schedule[day_name] = {
                    'date': day_date,
                    'count': day_appointments.count(),
                    'appointments': day_appointments,
                    'is_available': doctor.is_active and doctor.is_verified,
                    'is_weekend': day_offset >= 5,
                }
            weekly_schedule[doctor.id] = {
                'doctor': doctor,
                'schedule': doctor_schedule
            }
        
        # Get departments for filter
        departments = HospitalDepartment.objects.filter(
            hospital=hospital,
            active=True
        ).order_by('name')
        
        context = {
            'doctors': doctors,
            'total_doctors': total_doctors,
            'doctors_on_duty': doctors_on_duty,
            'available_doctors': available_doctors,
            'busy_doctors': busy_doctors,
            'today_count': today_count,
            'upcoming_count': upcoming_count,
            'weekly_schedule': weekly_schedule,
            'departments': departments,
            'today': today,
            'week_start': week_start,
            'week_end': week_end,
            'page_title': 'Doctor Schedule',
            'current_page': 'Doctor Schedule',
            'breadcrumb': 'Appointment Management / Doctor Schedule',
        }
        return render(request, self.template_name, context)
    
# =============================================================================
# SETTINGS DASHBOARD
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class SettingsDashboardView(HospitalAdminBaseView):
    """Settings dashboard."""
    template_name = 'hospital_admin/settings/dashboard.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        context = {
            'page_title': 'Settings',
            'current_page': 'Settings',
            'breadcrumb': 'Settings',
        }
        return render(request, self.template_name, context)


# =============================================================================
# PROFILE SETTINGS
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class ProfileSettingsView(HospitalAdminBaseView):
    """Profile settings."""
    template_name = 'hospital_admin/settings/profile.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        form = ProfileForm(instance=request.user)
        
        context = {
            'form': form,
            'user': request.user,
            'page_title': 'Profile Settings',
            'current_page': 'Profile Settings',
            'breadcrumb': 'Settings / Profile',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('hospital_admin:profile_settings')
        
        context = {
            'form': form,
            'user': request.user,
            'page_title': 'Profile Settings',
            'current_page': 'Profile Settings',
            'breadcrumb': 'Settings / Profile',
        }
        return render(request, self.template_name, context)


# =============================================================================
# CHANGE PASSWORD
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class ChangePasswordView(HospitalAdminBaseView):
    """Change password."""
    template_name = 'hospital_admin/settings/change_password.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        form = CustomPasswordChangeForm(user=request.user)
        
        context = {
            'form': form,
            'page_title': 'Change Password',
            'current_page': 'Change Password',
            'breadcrumb': 'Settings / Change Password',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('hospital_admin:change_password')
        
        context = {
            'form': form,
            'page_title': 'Change Password',
            'current_page': 'Change Password',
            'breadcrumb': 'Settings / Change Password',
        }
        return render(request, self.template_name, context)


# =============================================================================
# NOTIFICATION SETTINGS
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class NotificationSettingsView(HospitalAdminBaseView):
    """Notification preferences."""
    template_name = 'hospital_admin/settings/notifications.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        # Get user's notification settings (can be stored in a separate model)
        # For now, use session or defaults
        form = NotificationPreferencesForm()
        
        context = {
            'form': form,
            'page_title': 'Notification Preferences',
            'current_page': 'Notification Preferences',
            'breadcrumb': 'Settings / Notifications',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        form = NotificationPreferencesForm(request.POST)
        
        if form.is_valid():
            # Save notification preferences (you can store in User model or separate model)
            messages.success(request, 'Notification preferences updated successfully!')
            return redirect('hospital_admin:notification_settings')
        
        context = {
            'form': form,
            'page_title': 'Notification Preferences',
            'current_page': 'Notification Preferences',
            'breadcrumb': 'Settings / Notifications',
        }
        return render(request, self.template_name, context)


# =============================================================================
# SECURITY SETTINGS
# =============================================================================
@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class SecuritySettingsView(HospitalAdminBaseView):
    """Account security settings."""
    template_name = 'hospital_admin/settings/security.html'
    
    def get(self, request):
        if not self.is_verified:
            messages.warning(request, 'Please complete hospital verification first.')
            return redirect('hospital_admin:dashboard')
        
        context = {
            'user': request.user,
            'page_title': 'Account Security',
            'current_page': 'Account Security',
            'breadcrumb': 'Settings / Security',
        }
        return render(request, self.template_name, context)