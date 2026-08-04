# doctors/forms.py
from django import forms
from .models import Doctor, Specialty
from django.core.exceptions import ValidationError
from PIL import Image
from django.contrib.auth.forms import PasswordChangeForm
from .models import DoctorSettings
from django.contrib.auth.password_validation import validate_password
from .models import DoctorNotificationSettings

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = [
            'full_name', 'national_id', 'registration_number', 'gender',
            'date_of_birth', 'phone', 'email', 'address', 'city', 'district',
            'zip_code', 'specialties', 'hospital', 'qualification', 'experience',
            'consultation_fee', 'available_days', 'available_time_start',
            'available_time_end', 'profile_photo', 'bio', 'is_active', 'is_verified'
        ]
        widgets = {
            'specialties': forms.SelectMultiple(attrs={
                'class': 'form-select w-full rounded-xl border border-slate-600 bg-slate-700/50 focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200 py-2 px-4 text-slate-200 shadow-sm',
                'size': 5,  # Show multiple options at once
                'multiple': True,
            }),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'available_time_start': forms.TimeInput(attrs={'type': 'time'}),
            'available_time_end': forms.TimeInput(attrs={'type': 'time'}),
            'consultation_fee': forms.NumberInput(attrs={'step': '0.01'}),
            # অন্যান্য ফিল্ডের জন্য Tailwind CSS ক্লাস যোগ করুন
        }
        labels = {
            'specialties': 'Specialties',
        }
        help_texts = {
            'specialties': 'Hold Ctrl (Windows) or Cmd (Mac) to select multiple specialties.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # প্রতিটি ফিল্ডে Tailwind CSS ক্লাস যুক্ত করুন
        for field in self.fields.values():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, forms.URLInput)):
                field.widget.attrs['class'] = 'w-full rounded-xl border border-slate-600 bg-slate-700/50 focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 shadow-sm'
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'w-full rounded-xl border border-slate-600 bg-slate-700/50 focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 shadow-sm resize-none'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'custom-select w-full rounded-xl border border-slate-600 bg-slate-700/50 focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200 py-2 px-4 text-slate-200 shadow-sm'
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs['class'] = 'w-full rounded-xl border border-slate-600 bg-slate-700/50 focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition duration-200 py-2 px-4 text-slate-200 shadow-sm'
                
class DoctorProfileForm(forms.ModelForm):
    """Form for doctors to edit their profile information."""
    
    # Specializations field (ManyToMany)
    specialties = forms.ModelMultipleChoiceField(
        queryset=Specialty.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'specialty-checkbox-grid',
        }),
        required=False,
        label='Specializations'
    )
    
    class Meta:
        model = Doctor
        fields = [
            # Personal Information
            'full_name', 'phone', 'email', 'gender', 'date_of_birth',
            'address', 'city', 'district', 'zip_code',
            # Professional Information
            'qualification', 'experience', 'consultation_fee', 'bio',
            # Availability
            'available_days', 'available_time_start', 'available_time_end',
            # Specializations
            'specialties',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your full name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., 017XXXXXXXX',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'doctor@example.com',
            }),
            'gender': forms.Select(attrs={
                'class': 'form-input',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Enter your address',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your city',
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your district',
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter ZIP code',
            }),
            'qualification': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'e.g., MBBS, FCPS, MD',
            }),
            'experience': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
                'placeholder': 'Years of experience',
            }),
            'consultation_fee': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
                'step': '0.01',
                'placeholder': 'e.g., 500',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Write a short biography...',
                'maxlength': '1000',
            }),
            'available_days': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Monday, Wednesday, Friday',
            }),
            'available_time_start': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-input',
            }),
            'available_time_end': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make required fields
        self.fields['full_name'].required = True
        self.fields['phone'].required = True
        self.fields['email'].required = True
        
        # Set initial values for specialties
        if self.instance and self.instance.pk:
            self.fields['specialties'].initial = self.instance.specialties.all()
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            # Basic Bangladesh phone number validation
            import re
            if not re.match(r'^01[3-9]\d{8}$', phone):
                raise ValidationError("Enter a valid Bangladesh phone number (e.g., 017XXXXXXXX)")
        return phone
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email:
            from django.core.validators import validate_email
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Enter a valid email address.")
        return email
    
    def clean_experience(self):
        experience = self.cleaned_data.get('experience')
        if experience is not None and experience < 0:
            raise ValidationError("Experience cannot be negative.")
        return experience
    
    def clean_consultation_fee(self):
        fee = self.cleaned_data.get('consultation_fee')
        if fee is not None and fee < 0:
            raise ValidationError("Consultation fee cannot be negative.")
        return fee
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('available_time_start')
        end_time = cleaned_data.get('available_time_end')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Start time must be before end time.")
        
        return cleaned_data
    
class DoctorProfilePhotoForm(forms.ModelForm):
    """Form for updating doctor's profile picture."""
    
    class Meta:
        model = Doctor
        fields = ['profile_photo']
        widgets = {
            'profile_photo': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'profile-photo-input',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_photo'].required = False
        self.fields['profile_photo'].label = 'Profile Photo'
        self.fields['profile_photo'].help_text = 'Supported formats: JPG, PNG, WEBP. Max size: 5MB.'
    
    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        
        if not photo:
            return photo
        
        # Check file size (max 5MB)
        if photo.size > 5 * 1024 * 1024:
            raise ValidationError('Profile picture must be smaller than 5 MB.')
        
        # Check file extension
        valid_extensions = ['jpg', 'jpeg', 'png', 'webp']
        ext = photo.name.split('.')[-1].lower()
        if ext not in valid_extensions:
            raise ValidationError('Only JPG, PNG and WEBP images are allowed.')
        
        # Validate image using PIL
        try:
            img = Image.open(photo)
            img.verify()  # Verify image integrity
            
            # Re-open after verify
            img = Image.open(photo)
            
            # Check minimum dimensions
            width, height = img.size
            if width < 200 or height < 200:
                raise ValidationError('Image must be at least 200x200 pixels.')
            
            if width > 5000 or height > 5000:
                raise ValidationError('Image cannot exceed 5000x5000 pixels.')
            
        except Exception as e:
            raise ValidationError('Please upload a valid image.')
        
        return photo
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            # Delete old photo if it exists and is not the default
            if instance.pk:
                old_instance = instance.__class__.objects.get(pk=instance.pk)
                if old_instance.profile_photo and old_instance.profile_photo != instance.profile_photo:
                    old_instance.profile_photo.delete(save=False)
            
            instance.save()
        
        return instance
    
class DoctorPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form for doctors with enhanced validation.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom CSS classes to all fields
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-input password-input',
            'placeholder': 'Enter your current password',
            'autocomplete': 'current-password',
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-input password-input',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-input password-input',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        })
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            # Use Django's built-in password validators
            try:
                validate_password(password, self.user)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password
    
class DoctorGeneralSettingsForm(forms.ModelForm):
    """Form for doctor general settings."""
    
    class Meta:
        model = DoctorSettings
        fields = [
            'theme',
            'language',
            'timezone',
            'date_format',
            'time_format',
            'landing_page',
            'items_per_page',
        ]
        widgets = {
            'theme': forms.Select(attrs={
                'class': 'form-input',
            }),
            'language': forms.Select(attrs={
                'class': 'form-input',
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-input',
            }),
            'date_format': forms.Select(attrs={
                'class': 'form-input',
            }),
            'time_format': forms.Select(attrs={
                'class': 'form-input',
            }),
            'landing_page': forms.Select(attrs={
                'class': 'form-input',
            }),
            'items_per_page': forms.Select(attrs={
                'class': 'form-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add labels for better readability
        self.fields['theme'].label = 'Theme'
        self.fields['language'].label = 'Language'
        self.fields['timezone'].label = 'Time Zone'
        self.fields['date_format'].label = 'Date Format'
        self.fields['time_format'].label = 'Time Format'
        self.fields['landing_page'].label = 'Landing Page'
        self.fields['items_per_page'].label = 'Items Per Page'
        
class DoctorNotificationSettingsForm(forms.ModelForm):
    """Form for doctor notification settings."""
    
    class Meta:
        model = DoctorNotificationSettings
        fields = [
            # Appointment
            'appointment_enabled',
            'appointment_new',
            'appointment_approved',
            'appointment_cancelled',
            'appointment_rescheduled',
            'appointment_reminder',
            # Prescription
            'prescription_enabled',
            'prescription_viewed',
            'prescription_downloaded',
            'prescription_printed',
            # Laboratory
            'laboratory_enabled',
            'lab_request_created',
            'lab_sample_collected',
            'lab_testing_started',
            'lab_report_ready',
            'lab_report_verified',
            # Patient
            'patient_enabled',
            'patient_assigned',
            'followup_due',
            # System
            'system_enabled',
            'system_updates',
            'system_maintenance',
            'security_alerts',
            'new_features',
            # Delivery
            'email_enabled',
            'sms_enabled',
            'browser_enabled',
            # Frequency
            'frequency',
            # Quiet Hours
            'quiet_hours_enabled',
            'quiet_hours_start',
            'quiet_hours_end',
        ]
        widgets = {
            'appointment_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'appointment_new': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'appointment_approved': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'appointment_cancelled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'appointment_rescheduled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'appointment_reminder': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'prescription_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'prescription_viewed': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'prescription_downloaded': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'prescription_printed': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'laboratory_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'lab_request_created': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'lab_sample_collected': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'lab_testing_started': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'lab_report_ready': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'lab_report_verified': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'patient_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'patient_assigned': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'followup_due': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'system_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'system_updates': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'system_maintenance': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'security_alerts': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'new_features': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'email_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'sms_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'browser_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'frequency': forms.Select(attrs={'class': 'form-input'}),
            'quiet_hours_enabled': forms.CheckboxInput(attrs={'class': 'toggle-checkbox'}),
            'quiet_hours_start': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'quiet_hours_end': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all checkbox fields not required
        for field_name, field in self.fields.items():
            if isinstance(field, forms.BooleanField):
                field.required = False
    
    def clean(self):
        cleaned_data = super().clean()
        quiet_hours_enabled = cleaned_data.get('quiet_hours_enabled')
        quiet_hours_start = cleaned_data.get('quiet_hours_start')
        quiet_hours_end = cleaned_data.get('quiet_hours_end')
        
        if quiet_hours_enabled:
            if not quiet_hours_start:
                self.add_error('quiet_hours_start', 'Start time is required when quiet hours are enabled.')
            if not quiet_hours_end:
                self.add_error('quiet_hours_end', 'End time is required when quiet hours are enabled.')
            if quiet_hours_start and quiet_hours_end and quiet_hours_start >= quiet_hours_end:
                self.add_error('quiet_hours_end', 'End time must be after start time.')
        
        return cleaned_data
    
class DoctorCreateProfileForm(forms.ModelForm):
    """
    Form for doctors to create their initial profile.
    """
    
    class Meta:
        model = Doctor
        fields = [
            "registration_number",
            "national_id",
            "gender",
            "date_of_birth",
            "phone",
            "address",
            "city",
            "district",
            "zip_code",
            "qualification",
            "experience",
            "consultation_fee",
            "hospital",
            "specialties",
            "available_days",
            "available_time_start",
            "available_time_end",
            "bio",
            "profile_photo",
        ]
        widgets = {
            "registration_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "BMDC Registration Number",
                "required": True,
            }),
            "national_id": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "National ID (10 digits)",
                "required": True,
            }),
            "gender": forms.Select(attrs={
                "class": "form-control",
                "required": True,
            }),
            "date_of_birth": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
                "required": True,
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Phone Number",
                "required": True,
            }),
            "address": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Full Address",
            }),
            "city": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "City",
            }),
            "district": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "District",
            }),
            "zip_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Zip Code",
            }),
            "qualification": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "e.g., MBBS, FCPS, MD, MS",
                "required": True,
            }),
            "experience": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "placeholder": "Years of experience",
                "required": True,
            }),
            "consultation_fee": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "placeholder": "Consultation fee in BDT",
                "required": True,
            }),
            "hospital": forms.Select(attrs={
                "class": "form-control",
                "required": True,
            }),
            "specialties": forms.SelectMultiple(attrs={
                "class": "form-control",
                "required": True,
            }),
            "available_days": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Mon,Tue,Wed,Thu,Fri",
            }),
            "available_time_start": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control",
            }),
            "available_time_end": forms.TimeInput(attrs={
                "type": "time",
                "class": "form-control",
            }),
            "bio": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "Professional summary and expertise",
            }),
            "profile_photo": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
        }
        labels = {
            "registration_number": "BMDC Registration Number",
            "national_id": "National ID (NID)",
            "date_of_birth": "Date of Birth",
            "consultation_fee": "Consultation Fee (BDT)",
        }
        help_texts = {
            "registration_number": "Your BMDC registration number",
            "national_id": "Your 10-digit National ID number",
            "specialties": "Hold Ctrl/Cmd to select multiple specialties",
            "available_days": "Comma-separated days (e.g., Mon,Tue,Wed)",
            "profile_photo": "Upload a professional photo (PNG, JPG up to 5MB)",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all required fields visually marked
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' required'
    
    def clean_registration_number(self):
        registration_number = self.cleaned_data.get("registration_number")
        if registration_number:
            # Remove any whitespace
            registration_number = registration_number.strip().upper()
            # Check uniqueness
            if Doctor.objects.filter(registration_number=registration_number).exists():
                raise forms.ValidationError(
                    "This registration number already exists. Please verify your BMDC number."
                )
        return registration_number
    
    def clean_national_id(self):
        national_id = self.cleaned_data.get("national_id")
        if national_id:
            # Remove any whitespace
            national_id = national_id.strip()
            # Check length for NID (10 digits)
            if len(national_id) != 10 or not national_id.isdigit():
                raise forms.ValidationError(
                    "National ID must be exactly 10 digits."
                )
            # Check uniqueness
            if Doctor.objects.filter(national_id=national_id).exists():
                raise forms.ValidationError(
                    "This National ID already exists."
                )
        return national_id
    
    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            phone = phone.strip()
            # Check if phone contains only digits and plus sign
            if not all(c.isdigit() or c == '+' for c in phone):
                raise forms.ValidationError(
                    "Phone number must contain only digits and '+' sign."
                )
        return phone
    
    def clean_consultation_fee(self):
        fee = self.cleaned_data.get("consultation_fee")
        if fee is not None and fee < 0:
            raise forms.ValidationError(
                "Consultation fee cannot be negative."
            )
        return fee
    
    def clean_experience(self):
        experience = self.cleaned_data.get("experience")
        if experience is not None and experience < 0:
            raise forms.ValidationError(
                "Experience cannot be negative."
            )
        if experience is not None and experience > 60:
            raise forms.ValidationError(
                "Please enter a valid experience (max 60 years)."
            )
        return experience
    
    def clean_available_days(self):
        days = self.cleaned_data.get("available_days")
        if days:
            days = days.strip()
            valid_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            day_list = [d.strip() for d in days.split(',')]
            for day in day_list:
                if day not in valid_days:
                    raise forms.ValidationError(
                        f"'{day}' is not a valid day. Use: Mon, Tue, Wed, Thu, Fri, Sat, Sun"
                    )
        return days