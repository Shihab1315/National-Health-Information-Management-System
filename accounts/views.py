from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import SignupForm, UserEditForm
from .models import User
from django.contrib import messages
from django.views import View
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.views import View

from django.core.exceptions import ObjectDoesNotExist

from django.utils.decorators import method_decorator
from django.contrib.auth import logout
from .forms import LoginForm
class SignupView(View):
    """
    Production-ready signup view with role selection.
    """
    template_name = 'accounts/signup.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        
        form = SignupForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = SignupForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            
            # Success message
            messages.success(
                request,
                'Registration completed successfully. Please login to continue.'
            )
            
            return redirect('accounts:login')
        
        # Show error messages
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        
        return render(request, self.template_name, {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserEditForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})

class CustomLoginView(LoginView):
    """
    Custom login view - redirects all users to home page after login.
    """
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """Handle successful login - always redirect to home page."""
        user = form.get_user()
        
        # Login the user
        login(self.request, user)
        
        # Show welcome message
        messages.success(
            self.request,
            f'Welcome back, {user.get_full_name() or user.username}!'
        )
        
        # Always redirect to home page regardless of role
        return redirect('dashboard:homepage')
    
    def form_invalid(self, form):
        """Handle invalid login attempt."""
        messages.error(self.request, 'Invalid username/email or password.')
        return super().form_invalid(form)


@login_required
def dashboard_redirect(request):
    """
    Redirect logged-in users to their own dashboard based on role.
    """
    
    user = request.user

    # Super Admin
    if user.role == user.Role.SUPER_ADMIN:
        return redirect("superadmin:dashboard")

    # Doctor
    elif user.role == user.Role.DOCTOR:
        if hasattr(user, "doctor_profile"):
            return redirect("dashboard:doctor_dashboard")

        messages.error(
            request,
            "Doctor profile not found. Please contact the administrator."
        )
        return redirect("dashboard:homepage")

    # Patient
    elif user.role == user.Role.PATIENT:
        if hasattr(user, "patient_profile"):
            return redirect("dashboard:patient_dashboard")

        messages.error(
            request,
            "Patient profile not found. Please contact support."
        )
        return redirect("dashboard:homepage")

    # Hospital Admin
    elif user.role == user.Role.HOSPITAL_ADMIN:
        return redirect("accounts:hospital_admin_dashboard_check")

    # Receptionist
    elif user.role == user.Role.RECEPTIONIST:
        return redirect("receptionist:dashboard")

    # Lab Technician
    elif user.role == user.Role.LAB_TECHNICIAN:
        return redirect("laboratory:dashboard")

    # Pharmacist
    elif user.role == user.Role.PHARMACIST:
        return redirect("pharmacy:dashboard")

    # Unknown Role
    messages.warning(
        request,
        "No dashboard available for your account."
    )
    return redirect("dashboard:homepage")

@login_required
def hospital_admin_dashboard_check(request):
    """
    Check hospital admin application status before redirecting to dashboard.
    """
    from hospitals.models import HospitalApplication
    
    user = request.user
    
    try:
        application = HospitalApplication.objects.get(user=user)
    except HospitalApplication.DoesNotExist:
        messages.info(
            request,
            'Please complete your hospital registration to access the dashboard.'
        )
        return redirect('hospitals:create_application')
    
    # Check application status
    status = application.status
    
    if status == 'approved':
        if application.hospital:
            return redirect('hospital_admin:dashboard')
        else:
            messages.error(
                request,
                'Your hospital record is missing. Please contact administrator.'
            )
            return redirect('dashboard:homepage')
    
    elif status == 'draft':
        messages.info(
            request,
            'Please complete your hospital registration.'
        )
        return redirect('hospitals:edit_application', kwargs={'pk': application.pk})
    
    elif status == 'submitted':
        messages.info(
            request,
            'Your hospital application has been submitted and is pending review.'
        )
        return redirect('hospitals:application_status', kwargs={'pk': application.pk})
    
    elif status == 'under_review':
        messages.info(
            request,
            'Your hospital application is currently under review.'
        )
        return redirect('hospitals:application_status', kwargs={'pk': application.pk})
    
    elif status == 'need_more_info':
        messages.info(
            request,
            'Additional information is required for your application.'
        )
        return redirect('hospitals:edit_application', kwargs={'pk': application.pk})
    
    elif status == 'rejected':
        messages.warning(
            request,
            'Your hospital application has been rejected. Please check the reason and resubmit.'
        )
        return redirect('hospitals:application_status', kwargs={'pk': application.pk})
    
    # Default fallback
    return redirect('dashboard:homepage')

@login_required
def profile_view(request):
    """User profile view."""
    return render(request, 'accounts/profile.html', {'user': request.user})

# @method_decorator(login_required, name='dispatch')
# class DashboardRedirectView(View):
#     """
#     Centralized dashboard redirect view.
#     Redirects users to their role-specific dashboard.
#     """
    
#     def get(self, request):
#         user = request.user
#         role = user.role
        
#         # Check if user is active
#         if not user.is_active:
#             messages.error(request, 'Your account is inactive. Please contact administrator.')
#             return redirect('dashboard:homepage')
        
#         # Super Admin
#         if role == 'super_admin':
#             return self._redirect_super_admin(request)
        
#         # Hospital Admin
#         if role == 'hospital_admin':
#             return self._redirect_hospital_admin(request)
        
#         # Doctor
#         if role == 'doctor':
#             return self._redirect_doctor(request)
        
#         # Patient
#         if role == 'patient':
#             return self._redirect_patient(request)
        
#         # Unknown role
#         return self._handle_invalid_role(request)
    
#     def _redirect_super_admin(self, request):
#         """Redirect Super Admin to their dashboard."""
#         try:
#             return redirect('superadmin:dashboard')
#         except:
#             messages.error(request, 'Super Admin dashboard not found. Please contact administrator.')
#             return redirect('dashboard:homepage')
    
#     def _redirect_hospital_admin(self, request):
#         """Redirect Hospital Admin based on application status."""
#         from hospitals.models import HospitalApplication
        
#         user = request.user
        
#         try:
#             application = HospitalApplication.objects.get(user=user)
#         except HospitalApplication.DoesNotExist:
#             messages.info(
#                 request,
#                 'Please complete your hospital registration to access the dashboard.'
#             )
#             return redirect('hospitals:create_application')
        
#         # Check application status
#         status = application.status
        
#         if status == 'approved':
#             if application.hospital:
#                 messages.success(
#                     request,
#                     'Welcome to your hospital dashboard!'
#                 )
#                 return redirect('hospital_admin:dashboard')
#             else:
#                 messages.error(
#                     request,
#                     'Your hospital record is missing. Please contact administrator.'
#                 )
#                 return redirect('dashboard:homepage')
        
#         elif status == 'draft':
#             messages.info(
#                 request,
#                 'Please complete your hospital registration.'
#             )
#             return redirect('hospitals:edit_application', kwargs={'pk': application.pk})
        
#         elif status == 'submitted':
#             messages.info(
#                 request,
#                 'Your hospital application has been submitted and is pending review.'
#             )
#             return redirect('hospitals:application_status', kwargs={'pk': application.pk})
        
#         elif status == 'under_review':
#             messages.info(
#                 request,
#                 'Your hospital application is currently under review.'
#             )
#             return redirect('hospitals:application_status', kwargs={'pk': application.pk})
        
#         elif status == 'need_more_info':
#             messages.info(
#                 request,
#                 'Additional information is required for your application.'
#             )
#             return redirect('hospitals:edit_application', kwargs={'pk': application.pk})
        
#         elif status == 'rejected':
#             messages.warning(
#                 request,
#                 'Your hospital application has been rejected. Please check the reason and resubmit.'
#             )
#             return redirect('hospitals:application_status', kwargs={'pk': application.pk})
        
#         # Default fallback
#         messages.warning(request, 'Unable to determine application status. Please contact administrator.')
#         return redirect('dashboard:homepage')
    
#     def _redirect_doctor(self, request):
#         """Redirect Doctor to their dashboard."""
#         user = request.user
        
#         try:
#             doctor = user.doctor_profile
#             return redirect('dashboard:doctor_dashboard')
#         except ObjectDoesNotExist:
#             messages.error(
#                 request,
#                 'Your doctor profile is missing. Please contact the administrator.'
#             )
#             return redirect('dashboard:homepage')
    
#     def _redirect_patient(self, request):
#         """Redirect Patient to their dashboard."""
#         user = request.user
        
#         try:
#             patient = user.patient_profile
#             return redirect('dashboard:patient_dashboard')
#         except ObjectDoesNotExist:
#             messages.error(
#                 request,
#                 'Your patient profile is missing. Please contact support.'
#             )
#             return redirect('dashboard:homepage')
    
#     def _handle_invalid_role(self, request):
#         """Handle invalid or unknown role."""
#         # Logout the user
#         logout(request)
        
#         messages.error(
#             request,
#             'Invalid user role. Please contact administrator.'
#         )
#         return redirect('dashboard:homepage')