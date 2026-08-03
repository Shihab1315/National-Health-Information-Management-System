# doctors/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Doctor, Specialty
from .forms import DoctorForm
from accounts.decorators import role_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from appointments.models import Appointment
from prescriptions.models import Prescription
from django.http import JsonResponse

from django.views import View
from .forms import DoctorProfilePhotoForm
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .forms import DoctorPasswordChangeForm
from laboratory.models import LabOrder
from django.db import transaction
from .forms import DoctorProfileForm
from .models import DoctorSettings
from .forms import DoctorGeneralSettingsForm
from .models import DoctorNotificationSettings
from .forms import DoctorNotificationSettingsForm
from notifications.models import Notification


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_list(request):
    doctors = Doctor.objects.all()

    # Search
    search_query = request.GET.get('q')
    if search_query:
        doctors = doctors.filter(
            Q(full_name__icontains=search_query) |
            Q(doctor_id__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(specialties__name__icontains=search_query)
        ).distinct()

    # Filter by specialty
    specialty_filter = request.GET.get('specialty')
    if specialty_filter:
        doctors = doctors.filter(specialties__id=specialty_filter)

    # Filter by hospital
    hospital_filter = request.GET.get('hospital')
    if hospital_filter:
        doctors = doctors.filter(hospital__id=hospital_filter)

    # Filter by district
    district_filter = request.GET.get('district')
    if district_filter:
        doctors = doctors.filter(district=district_filter)

    # Pagination
    paginator = Paginator(doctors, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get distinct filters for dropdowns
    specialties = Specialty.objects.filter(is_active=True).order_by('name')
    districts = Doctor.objects.exclude(district__isnull=True).exclude(district='').values_list('district', flat=True).distinct().order_by('district')

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'specialty_filter': specialty_filter,
        'hospital_filter': hospital_filter,
        'district_filter': district_filter,
        'specialties': specialties,
        'districts': districts,
    }
    return render(request, 'doctors/doctor_list.html', context)


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    return render(request, 'doctors/doctor_detail.html', {'doctor': doctor})


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'Doctor {doctor.full_name} added successfully!')
            return redirect('doctors:detail', pk=doctor.pk)
    else:
        form = DoctorForm()
    
    # (ঐচ্ছিক) টেমপ্লেটে প্রয়োজনে সব স্পেশালিটি পাস করা
    specialties = Specialty.objects.filter(is_active=True).order_by('name')
    context = {
        'form': form,
        'title': 'Add New Doctor',
        'specialties': specialties,  # টেমপ্লেটে ব্যবহার করতে পারেন
    }
    return render(request, 'doctors/doctor_form.html', context)


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_update(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Doctor {doctor.full_name} updated successfully!')
            return redirect('doctors:detail', pk=doctor.pk)
    else:
        form = DoctorForm(instance=doctor)
    
    specialties = Specialty.objects.filter(is_active=True).order_by('name')
    context = {
        'form': form,
        'title': 'Edit Doctor',
        'doctor': doctor,
        'specialties': specialties,
    }
    return render(request, 'doctors/doctor_form.html', context)


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_delete(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        doctor.delete()
        messages.success(request, 'Doctor deleted successfully.')
        return redirect('doctors:list')
    return render(request, 'doctors/doctor_confirm_delete.html', {'doctor': doctor})

@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorProfileView(View):
    """
    Doctor Profile View.
    Displays the logged-in doctor's complete profile information.
    """
    template_name = 'doctors/doctor/my_profile.html'
    
    def get(self, request):
        # Get the logged-in doctor
        try:
            doctor = Doctor.objects.select_related(
                'user', 
                'hospital'
            ).prefetch_related(
                'specialties'
            ).get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect('dashboard:doctor_dashboard')
        
        # Get statistics
        appointment_count = Appointment.objects.filter(doctor=doctor, deleted_at__isnull=True).count()
        completed_count = Appointment.objects.filter(doctor=doctor, status='completed', deleted_at__isnull=True).count()
        pending_count = Appointment.objects.filter(doctor=doctor, status='pending', deleted_at__isnull=True).count()
        
        prescription_count = Prescription.objects.filter(doctor=doctor, deleted_at__isnull=True).count()
        lab_request_count = LabOrder.objects.filter(doctor=doctor, deleted_at__isnull=True).count()
        notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        
        # Calculate profile completion
        profile_completion = self._calculate_completion(doctor)
        
        # Prepare availability
        available_days = doctor.available_days.split(',') if doctor.available_days else []
        
        context = {
            'doctor': doctor,
            'hospital': doctor.hospital,
            'specialties': doctor.specialties.all(),
            'available_days': available_days,
            'appointment_count': appointment_count,
            'completed_count': completed_count,
            'pending_count': pending_count,
            'prescription_count': prescription_count,
            'lab_request_count': lab_request_count,
            'notification_count': notification_count,
            'profile_completion': profile_completion,
            'today': timezone.now().date(),
            'age': self._calculate_age(doctor.date_of_birth) if doctor.date_of_birth else None,
        }
        
        return render(request, self.template_name, context)
    
    def _calculate_age(self, date_of_birth):
        """Calculate age from date of birth."""
        if not date_of_birth:
            return None
        today = timezone.now().date()
        age = today.year - date_of_birth.year
        if today.month < date_of_birth.month or \
           (today.month == date_of_birth.month and today.day < date_of_birth.day):
            age -= 1
        return age
    
    def _calculate_completion(self, doctor):
        """Calculate profile completion percentage."""
        fields = {
            'profile_photo': doctor.profile_photo is not None,
            'phone': bool(doctor.phone),
            'email': bool(doctor.email),
            'qualification': bool(doctor.qualification),
            'experience': doctor.experience > 0,
            'bio': bool(doctor.bio),
            'available_days': bool(doctor.available_days),
            'consultation_fee': doctor.consultation_fee > 0,
            'specialties': doctor.specialties.exists(),
        }
        
        completed = sum(1 for v in fields.values() if v)
        total = len(fields)
        
        return int((completed / total) * 100)
    
@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorProfileUpdateView(View):
    """
    Doctor Profile Update View.
    Allows doctors to edit their own profile information.
    """
    template_name = 'doctors/doctor/edit_profile.html'
    
    def get(self, request):
        try:
            doctor = Doctor.objects.select_related(
                'user', 'hospital'
            ).prefetch_related(
                'specialties'
            ).get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect('dashboard:doctor_dashboard')
        
        form = DoctorProfileForm(instance=doctor)
        
        context = {
            'doctor': doctor,
            'form': form,
            'hospital': doctor.hospital,
            'specialties': doctor.specialties.all(),
            'all_specialties': Specialty.objects.filter(is_active=True),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        try:
            doctor = Doctor.objects.select_related(
                'user', 'hospital'
            ).prefetch_related(
                'specialties'
            ).get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect('dashboard:doctor_dashboard')
        
        form = DoctorProfileForm(request.POST, instance=doctor)
        
        # ===== DEBUG =====
        print("=" * 60)
        print("POST DATA RECEIVED:")
        for key, value in request.POST.items():
            print(f"  {key}: {value}")
        print("=" * 60)
        
        if form.is_valid():
            print("✅ Form is valid")
            print("Cleaned data:")
            for key, value in form.cleaned_data.items():
                print(f"  {key}: {value}")
            print("=" * 60)
            
            try:
                with transaction.atomic():
                    updated_doctor = form.save()
                    specialties = form.cleaned_data.get('specialties')
                    if specialties is not None:
                        updated_doctor.specialties.set(specialties)
                    
                    # ===== DEBUG =====
                    print(f"✅ Doctor saved: {updated_doctor.full_name}")
                    print(f"   Phone: {updated_doctor.phone}")
                    print(f"   Email: {updated_doctor.email}")
                    print(f"   Gender: {updated_doctor.gender}")
                    print(f"   DOB: {updated_doctor.date_of_birth}")
                    print("=" * 60)
                    
                    messages.success(request, "✅ Profile updated successfully.")
                    return redirect('doctors:doctor_profile')
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                messages.error(request, f"Error updating profile: {str(e)}")
        else:
            print("❌ Form is invalid:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"  {field}: {error}")
                    messages.error(request, f"{field}: {error}")
        
        context = {
            'doctor': doctor,
            'form': form,
            'hospital': doctor.hospital,
            'specialties': doctor.specialties.all(),
            'all_specialties': Specialty.objects.filter(is_active=True),
        }
        
        return render(request, self.template_name, context)
    
@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorProfilePhotoUpdateView(View):
    """
    Doctor Profile Photo Update View.
    Allows doctors to upload, change, or remove their profile picture.
    """
    template_name = 'doctors/doctor/change_profile_picture.html'
    
    def get(self, request):
        try:
            doctor = Doctor.objects.select_related('user').get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect('dashboard:doctor_dashboard')
        
        form = DoctorProfilePhotoForm(instance=doctor)
        
        context = {
            'doctor': doctor,
            'form': form,
            'current_photo': doctor.profile_photo,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        try:
            doctor = Doctor.objects.select_related('user').get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect('dashboard:doctor_dashboard')
        
        form = DoctorProfilePhotoForm(request.POST, request.FILES, instance=doctor)
        
        if form.is_valid():
            # Save the form (this will handle old image deletion)
            form.save()
            messages.success(request, "✅ Profile picture updated successfully.")
            return redirect('doctors:doctor_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
        
        context = {
            'doctor': doctor,
            'form': form,
            'current_photo': doctor.profile_photo,
        }
        
        return render(request, self.template_name, context)


@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorProfilePhotoRemoveView(View):
    """
    Doctor Profile Photo Remove View.
    Allows doctors to remove their profile picture.
    """
    
    def post(self, request):
        try:
            doctor = Doctor.objects.select_related('user').get(user=request.user)
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect('dashboard:doctor_dashboard')
        
        if doctor.profile_photo:
            # Delete the image file
            doctor.profile_photo.delete(save=False)
            doctor.profile_photo = None
            doctor.save()
            messages.success(request, "✅ Profile picture removed successfully.")
        else:
            messages.info(request, "You don't have a profile picture to remove.")
        
        return redirect('doctors:doctor_profile')
    
@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorChangePasswordView(PasswordChangeView):
    """
    Doctor Change Password View.
    Allows doctors to securely change their account password.
    """
    template_name = 'doctors/doctor/change_password.html'
    form_class = DoctorPasswordChangeForm
    success_url = reverse_lazy('doctors:doctor_profile')
    
    def form_valid(self, form):
        # Save the new password
        form.save()
        
        # Update session hash to keep user logged in
        update_session_auth_hash(self.request, form.user)
        
        # Success message
        messages.success(self.request, "✅ Password changed successfully.")
        
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        # Display error messages
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, error)
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            doctor = self.request.user.doctor_profile
        except:
            doctor = None
        context['doctor'] = doctor
        return context
    
@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorGeneralSettingsView(View):
    """
    Doctor General Settings View.
    Allows doctors to manage their personal application preferences.
    """
    template_name = 'doctors/doctor/general_settings.html'
    
    def get(self, request):
        # Get or create settings for the logged-in user
        settings, created = DoctorSettings.objects.get_or_create(user=request.user)
        
        form = DoctorGeneralSettingsForm(instance=settings)
        
        context = {
            'doctor': request.user.doctor_profile if hasattr(request.user, 'doctor_profile') else None,
            'settings': settings,
            'form': form,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Get the settings for the logged-in user
        settings, created = DoctorSettings.objects.get_or_create(user=request.user)
        
        form = DoctorGeneralSettingsForm(request.POST, instance=settings)
        
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Settings saved successfully.")
            return redirect('doctors:doctor_general_settings')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        context = {
            'doctor': request.user.doctor_profile if hasattr(request.user, 'doctor_profile') else None,
            'settings': settings,
            'form': form,
        }
        
        return render(request, self.template_name, context)
    
@method_decorator([login_required, role_required(['doctor'])], name='dispatch')
class DoctorNotificationSettingsView(View):
    """
    Doctor Notification Settings View.
    Allows doctors to manage their notification preferences.
    """
    template_name = 'doctors/doctor/notification_settings.html'
    
    def get(self, request):
        # Get or create notification settings for the logged-in user
        settings, created = DoctorNotificationSettings.objects.get_or_create(user=request.user)
        
        form = DoctorNotificationSettingsForm(instance=settings)
        
        context = {
            'doctor': request.user.doctor_profile if hasattr(request.user, 'doctor_profile') else None,
            'settings': settings,
            'form': form,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Get the notification settings for the logged-in user
        settings, created = DoctorNotificationSettings.objects.get_or_create(user=request.user)
        
        form = DoctorNotificationSettingsForm(request.POST, instance=settings)
        
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Notification settings updated successfully.")
            return redirect('doctors:doctor_notification_settings')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        context = {
            'doctor': request.user.doctor_profile if hasattr(request.user, 'doctor_profile') else None,
            'settings': settings,
            'form': form,
        }
        
        return render(request, self.template_name, context)


@login_required
@role_required(['doctor'])
def doctor_verification(request):
    """
    Doctor Verification page.
    Shows verification status and allows doctors to submit for verification.
    """
    try:
        doctor = Doctor.objects.select_related('user', 'hospital').prefetch_related('specialties').get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect('dashboard:doctor_dashboard')
    
    is_verified = doctor.is_verified
    
    # Get verification checklist
    checklist = {
        'personal_info': bool(doctor.user.get_full_name() and doctor.user.email),
        'bmdc_registration': bool(doctor.registration_number and doctor.registration_number != '000000'),
        'medical_degree': bool(doctor.qualification),
        'experience': bool(doctor.experience and doctor.experience > 0),
        'hospital_assignment': bool(doctor.hospital),
        'specialization': doctor.specialties.exists(),
        'government_id': bool(doctor.national_id and doctor.national_id != '0000000000'),
        'profile_photo': bool(doctor.profile_photo),
    }
    
    context = {
        'doctor': doctor,
        'is_verified': is_verified,
        'checklist': checklist,
        'page_title': 'Verification',
        'current_page': 'Verification',
    }
    return render(request, 'doctors/verification.html', context)
