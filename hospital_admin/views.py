# hospital_admin/views.py - Add the HospitalInformationView

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from accounts.decorators import role_required
from hospitals.models import HospitalApplication, Hospital
from django.utils import timezone
from .forms import HospitalInformationForm, HospitalContactInformationForm,HospitalAddressInformationForm, HospitalDocumentsForm


# =============================================================================
# BASE VIEW WITH VERIFICATION CHECK
# =============================================================================
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
                return redirect('/hospital-admin/verification/documents/')
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