# hospital_admin/forms.py
from django import forms
from django.core.exceptions import ValidationError
from hospitals.models import HospitalApplication
import re
from hospitals.models import HospitalDepartment, Hospital, Room
from doctors.models import Doctor
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from lab_technicians.models import LabTechnician

User = get_user_model()

class HospitalInformationForm(forms.ModelForm):
    """Form for hospital information step."""
    
    class Meta:
        model = HospitalApplication
        fields = [
            'hospital_name',
            'hospital_type',
            'license_number',
            'registration_number',
            'description',
        ]
        widgets = {
            'hospital_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter hospital name'
            }),
            'hospital_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter license number'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter registration number'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
                'placeholder': 'Brief description of your hospital',
                'rows': 4
            }),
        }
        labels = {
            'hospital_name': 'Hospital Name',
            'hospital_type': 'Hospital Type',
            'license_number': 'License Number',
            'registration_number': 'Registration Number',
            'description': 'Description',
        }
        help_texts = {
            'description': 'Provide a brief overview of your hospital (max 1000 characters).',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add required field indicators
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label} *"
    
    def clean_license_number(self):
        """Validate license number is unique."""
        license_number = self.cleaned_data.get('license_number')
        if license_number:
            # Check if license number exists for other applications
            instance = self.instance
            qs = HospitalApplication.objects.filter(license_number=license_number)
            if instance and instance.pk:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise ValidationError('This license number is already registered.')
        return license_number
    
    def clean_registration_number(self):
        """Validate registration number is unique."""
        registration_number = self.cleaned_data.get('registration_number')
        if registration_number:
            # Check if registration number exists for other applications
            instance = self.instance
            qs = HospitalApplication.objects.filter(registration_number=registration_number)
            if instance and instance.pk:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise ValidationError('This registration number is already registered.')
        return registration_number
    
    def clean_description(self):
        """Validate description length."""
        description = self.cleaned_data.get('description')
        if description and len(description) > 1000:
            raise ValidationError('Description must be less than 1000 characters.')
        return description
    
class HospitalContactInformationForm(forms.ModelForm):
    """Form for hospital contact information step."""
    
    class Meta:
        model = HospitalApplication
        fields = [
            'hospital_email',
            'phone',
            'emergency_phone',
            'website',
        ]
        widgets = {
            'hospital_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'hospital@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': '017XXXXXXXX'
            }),
            'emergency_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': '019XXXXXXXX (Optional)'
            }),
            'website': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'https://hospital.com (Optional)'
            }),
        }
        labels = {
            'hospital_email': 'Hospital Email',
            'phone': 'Phone Number',
            'emergency_phone': 'Emergency Phone',
            'website': 'Website',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add required field indicators
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label} *"
    
    def clean_phone(self):
        """Validate Bangladesh phone number."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any non-digit characters except +
            phone = re.sub(r'[^\d+]', '', phone)
            
            # Check if phone number is valid (Bangladesh format)
            if not re.match(r'^\+?8801[3-9]\d{8}$|^01[3-9]\d{8}$', phone):
                raise ValidationError('Enter a valid Bangladesh phone number (e.g., 017XXXXXXXX or +88017XXXXXXXX).')
        return phone
    
    def clean_emergency_phone(self):
        """Validate emergency phone number (optional)."""
        emergency_phone = self.cleaned_data.get('emergency_phone')
        if emergency_phone:
            # Remove any non-digit characters except +
            emergency_phone = re.sub(r'[^\d+]', '', emergency_phone)
            
            # Check if phone number is valid (Bangladesh format)
            if not re.match(r'^\+?8801[3-9]\d{8}$|^01[3-9]\d{8}$', emergency_phone):
                raise ValidationError('Enter a valid Bangladesh phone number (e.g., 019XXXXXXXX).')
        return emergency_phone
    
    def clean_website(self):
        """Validate website URL (optional)."""
        website = self.cleaned_data.get('website')
        if website:
            # Add https:// if no protocol is specified
            if not website.startswith(('http://', 'https://')):
                website = f'https://{website}'
        return website
    
class HospitalAddressInformationForm(forms.ModelForm):
    """Form for hospital address information step."""
    
    class Meta:
        model = HospitalApplication
        fields = [
            'division',
            'district',
            'upazila',
            'area',
            'postal_code',
            'full_address',
            'google_map_link',
            'latitude',
            'longitude',
        ]
        widgets = {
            'division': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter division (e.g., Dhaka)'
            }),
            'district': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter district (e.g., Dhaka)'
            }),
            'upazila': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter upazila/sub-district'
            }),
            'area': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter area/locality'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter postal code (e.g., 1207)'
            }),
            'full_address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
                'placeholder': 'House, Road, Area, District',
                'rows': 4
            }),
            'google_map_link': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'https://maps.google.com/...'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': '23.810331',
                'step': '0.000001'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': '90.412521',
                'step': '0.000001'
            }),
        }
        labels = {
            'division': 'Division',
            'district': 'District',
            'upazila': 'Upazila',
            'area': 'Area',
            'postal_code': 'Postal Code',
            'full_address': 'Full Address',
            'google_map_link': 'Google Map Link',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add required field indicators
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label} *"
    
    def clean_division(self):
        """Validate division is provided."""
        division = self.cleaned_data.get('division')
        if not division:
            raise ValidationError('Please enter the division.')
        return division
    
    def clean_district(self):
        """Validate district is provided."""
        district = self.cleaned_data.get('district')
        if not district:
            raise ValidationError('Please enter the district.')
        return district
    
    def clean_full_address(self):
        """Validate full address is provided."""
        full_address = self.cleaned_data.get('full_address')
        if not full_address:
            raise ValidationError('Please enter the full address.')
        return full_address
    
    def clean_postal_code(self):
        """Validate postal code format (optional)."""
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code:
            # Remove any non-digit characters
            import re
            postal_code = re.sub(r'[^\d]', '', postal_code)
            if len(postal_code) != 4:
                raise ValidationError('Postal code must be 4 digits (e.g., 1207).')
        return postal_code
    
    def clean_google_map_link(self):
        """Validate Google Map link URL (optional)."""
        google_map_link = self.cleaned_data.get('google_map_link')
        if google_map_link:
            if not google_map_link.startswith(('http://', 'https://')):
                google_map_link = f'https://{google_map_link}'
        return google_map_link
    
    def clean_latitude(self):
        """Validate latitude is between -90 and 90."""
        latitude = self.cleaned_data.get('latitude')
        if latitude is not None:
            if latitude < -90 or latitude > 90:
                raise ValidationError('Latitude must be between -90 and 90.')
        return latitude
    
    def clean_longitude(self):
        """Validate longitude is between -180 and 180."""
        longitude = self.cleaned_data.get('longitude')
        if longitude is not None:
            if longitude < -180 or longitude > 180:
                raise ValidationError('Longitude must be between -180 and 180.')
        return longitude
    
class HospitalDocumentsForm(forms.ModelForm):
    """Form for hospital documents upload step."""
    
    class Meta:
        model = HospitalApplication
        fields = [
            'logo',
            'trade_license',
            'hospital_license',
            'govt_approval',
            'tin_certificate',
            'other_documents',
        ]
        widgets = {
            'logo': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': 'image/jpeg,image/png,image/webp'
            }),
            'trade_license': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': '.pdf,image/jpeg,image/png'
            }),
            'hospital_license': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': '.pdf,image/jpeg,image/png'
            }),
            'govt_approval': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': '.pdf,image/jpeg,image/png'
            }),
            'tin_certificate': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': '.pdf,image/jpeg,image/png'
            }),
            'other_documents': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': '.pdf,image/jpeg,image/png'
            }),
        }
        labels = {
            'logo': 'Hospital Logo',
            'trade_license': 'Trade License',
            'hospital_license': 'Hospital License',
            'govt_approval': 'Government Approval',
            'tin_certificate': 'TIN Certificate',
            'other_documents': 'Other Documents',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make trade_license and hospital_license required
        self.fields['trade_license'].required = True
        self.fields['hospital_license'].required = True
        
        # Add help texts
        self.fields['logo'].help_text = 'JPG, JPEG, PNG, WEBP (Max 10MB)'
        self.fields['trade_license'].help_text = 'PDF, JPG, PNG (Max 10MB)'
        self.fields['hospital_license'].help_text = 'PDF, JPG, PNG (Max 10MB)'
        self.fields['govt_approval'].help_text = 'PDF, JPG, PNG (Max 10MB) (Optional)'
        self.fields['tin_certificate'].help_text = 'PDF, JPG, PNG (Max 10MB) (Optional)'
        self.fields['other_documents'].help_text = 'PDF, JPG, PNG (Max 10MB) (Optional)'
    
    def clean_logo(self):
        """Validate logo file."""
        logo = self.cleaned_data.get('logo')
        if logo:
            # Check file size (max 10MB)
            if logo.size > 10 * 1024 * 1024:
                raise ValidationError('Maximum allowed file size is 10 MB.')
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp']
            ext = logo.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Invalid file format. Allowed: JPG, JPEG, PNG, WEBP.')
        return logo
    
    def clean_trade_license(self):
        """Validate trade license file."""
        trade_license = self.cleaned_data.get('trade_license')
        if not trade_license:
            raise ValidationError('Trade License is required.')
        
        if trade_license:
            # Check file size (max 10MB)
            if trade_license.size > 10 * 1024 * 1024:
                raise ValidationError('Maximum allowed file size is 10 MB.')
            
            # Check file extension
            valid_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            ext = trade_license.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Invalid file format. Allowed: PDF, JPG, PNG.')
        return trade_license
    
    def clean_hospital_license(self):
        """Validate hospital license file."""
        hospital_license = self.cleaned_data.get('hospital_license')
        if not hospital_license:
            raise ValidationError('Hospital License is required.')
        
        if hospital_license:
            # Check file size (max 10MB)
            if hospital_license.size > 10 * 1024 * 1024:
                raise ValidationError('Maximum allowed file size is 10 MB.')
            
            # Check file extension
            valid_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            ext = hospital_license.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Invalid file format. Allowed: PDF, JPG, PNG.')
        return hospital_license
    
    def clean_govt_approval(self):
        """Validate government approval file (optional)."""
        govt_approval = self.cleaned_data.get('govt_approval')
        if govt_approval:
            # Check file size (max 10MB)
            if govt_approval.size > 10 * 1024 * 1024:
                raise ValidationError('Maximum allowed file size is 10 MB.')
            
            # Check file extension
            valid_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            ext = govt_approval.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Invalid file format. Allowed: PDF, JPG, PNG.')
        return govt_approval
    
    def clean_tin_certificate(self):
        """Validate TIN certificate file (optional)."""
        tin_certificate = self.cleaned_data.get('tin_certificate')
        if tin_certificate:
            # Check file size (max 10MB)
            if tin_certificate.size > 10 * 1024 * 1024:
                raise ValidationError('Maximum allowed file size is 10 MB.')
            
            # Check file extension
            valid_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            ext = tin_certificate.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Invalid file format. Allowed: PDF, JPG, PNG.')
        return tin_certificate
    
    def clean_other_documents(self):
        """Validate other documents file (optional)."""
        other_documents = self.cleaned_data.get('other_documents')
        if other_documents:
            # Check file size (max 10MB)
            if other_documents.size > 10 * 1024 * 1024:
                raise ValidationError('Maximum allowed file size is 10 MB.')
            
            # Check file extension
            valid_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            ext = other_documents.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Invalid file format. Allowed: PDF, JPG, PNG.')
        return other_documents
    
class DepartmentForm(forms.ModelForm):
    """Form for creating/updating departments."""
    
    # Additional fields for the form
    floor_number = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter floor number'
        })
    )
    
    room_number = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter room number'
        })
    )
    
    building_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter building name'
        })
    )
    
    block = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter block name'
        })
    )
    
    extension_number = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter extension number'
        })
    )
    
    max_doctors = forms.IntegerField(
        required=False,
        min_value=0,
        initial=10,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum doctors'
        })
    )
    
    max_nurses = forms.IntegerField(
        required=False,
        min_value=0,
        initial=20,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum nurses'
        })
    )
    
    max_beds = forms.IntegerField(
        required=False,
        min_value=0,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum beds'
        })
    )
    
    max_rooms = forms.IntegerField(
        required=False,
        min_value=0,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum rooms'
        })
    )
    
    opening_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition'
        })
    )
    
    closing_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition'
        })
    )
    
    open_24_hours = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )
    
    # Facilities checkboxes
    emergency_service = forms.BooleanField(required=False, initial=False)
    icu = forms.BooleanField(required=False, initial=False)
    operation_theater = forms.BooleanField(required=False, initial=False)
    laboratory = forms.BooleanField(required=False, initial=False)
    pharmacy = forms.BooleanField(required=False, initial=False)
    waiting_area = forms.BooleanField(required=False, initial=False)
    reception = forms.BooleanField(required=False, initial=False)
    wheelchair_accessible = forms.BooleanField(required=False, initial=False)
    twenty_four_hours = forms.BooleanField(required=False, initial=False)
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
            'placeholder': 'Enter any additional notes about this department...'
        })
    )
    
    class Meta:
        model = HospitalDepartment
        fields = [
            'name',
            'description',
            'phone',
            'email',
            'head_doctor',
            'active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter department name'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
                'placeholder': 'Enter department description'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter phone number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter email address'
            }),
            'head_doctor': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital', None)
        super().__init__(*args, **kwargs)
        
        # Set hospital in instance if not set
        if self.hospital:
            self.instance.hospital = self.hospital
        
        # Add placeholders and labels
        self.fields['name'].label = 'Department Name *'
        self.fields['description'].label = 'Description *'
        self.fields['phone'].label = 'Department Phone'
        self.fields['email'].label = 'Department Email'
        self.fields['head_doctor'].label = 'Department Head'
        self.fields['active'].label = 'Active'
        
        # Filter head_doctor choices to only verified doctors in the current hospital
        if self.hospital:
            from doctors.models import Doctor
            doctors = Doctor.objects.filter(
                hospital=self.hospital,
                is_verified=True,
                is_active=True
            ).select_related('user')
            
            choices = [('', 'Not Assigned')]
            for doctor in doctors:
                display_name = doctor.user.get_full_name() or doctor.user.username
                choices.append((doctor.id, f'Dr. {display_name}'))
            
            self.fields['head_doctor'].choices = choices
    
    def clean_name(self):
        """Validate department name is unique within the hospital."""
        name = self.cleaned_data.get('name')
        if name and self.hospital:
            existing = HospitalDepartment.objects.filter(
                hospital=self.hospital,
                name__iexact=name
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError('A department with this name already exists in your hospital.')
        return name
    
    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone:
            import re
            # Remove any non-digit characters
            phone = re.sub(r'[^\d+]', '', phone)
            if len(phone) < 10:
                raise ValidationError('Enter a valid phone number.')
        return phone
    
    def clean_email(self):
        """Validate email format."""
        email = self.cleaned_data.get('email')
        if email:
            from django.core.validators import validate_email
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError('Enter a valid email address.')
        return email
    
    def clean(self):
        """Validate working hours."""
        cleaned_data = super().clean()
        opening_time = cleaned_data.get('opening_time')
        closing_time = cleaned_data.get('closing_time')
        open_24_hours = cleaned_data.get('open_24_hours')
        
        if not open_24_hours and opening_time and closing_time and closing_time <= opening_time:
            raise ValidationError('Closing time must be after opening time.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the form."""
        instance = super().save(commit=False)
        
        # Set hospital if not set
        if self.hospital and not instance.hospital_id:
            instance.hospital = self.hospital
        
        if commit:
            instance.save()
        
        return instance


class DepartmentHeadForm(forms.Form):
    """Form for assigning department head."""
    
    head_doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
        })
    )
    
    def __init__(self, *args, **kwargs):
        hospital = kwargs.pop('hospital', None)
        super().__init__(*args, **kwargs)
        
        if hospital:
            self.fields['head_doctor'].queryset = Doctor.objects.filter(
                hospital=hospital,
                is_verified=True,
                is_active=True
            ).select_related('user')
            
class EditDepartmentForm(forms.ModelForm):
    """Form for editing departments."""
    
    # Additional fields for the form
    department_type = forms.ChoiceField(
        choices=[
            ('', 'Select Type'),
            ('medical', 'Medical'),
            ('surgical', 'Surgical'),
            ('diagnostic', 'Diagnostic'),
            ('emergency', 'Emergency'),
            ('administrative', 'Administrative'),
            ('support_service', 'Support Service'),
            ('specialized', 'Specialized'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
        })
    )
    
    floor_number = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter floor number'
        })
    )
    
    room_number = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter room number'
        })
    )
    
    building_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter building name'
        })
    )
    
    block = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter block name'
        })
    )
    
    extension_number = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Enter extension number'
        })
    )
    
    max_doctors = forms.IntegerField(
        required=False,
        min_value=0,
        initial=10,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum doctors'
        })
    )
    
    max_nurses = forms.IntegerField(
        required=False,
        min_value=0,
        initial=20,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum nurses'
        })
    )
    
    max_beds = forms.IntegerField(
        required=False,
        min_value=0,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum beds'
        })
    )
    
    max_rooms = forms.IntegerField(
        required=False,
        min_value=0,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
            'placeholder': 'Maximum rooms'
        })
    )
    
    opening_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition'
        })
    )
    
    closing_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition'
        })
    )
    
    open_24_hours = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )
    
    # Facilities checkboxes
    emergency_service = forms.BooleanField(required=False, initial=False)
    icu = forms.BooleanField(required=False, initial=False)
    operation_theater = forms.BooleanField(required=False, initial=False)
    laboratory = forms.BooleanField(required=False, initial=False)
    pharmacy = forms.BooleanField(required=False, initial=False)
    waiting_area = forms.BooleanField(required=False, initial=False)
    reception = forms.BooleanField(required=False, initial=False)
    wheelchair_accessible = forms.BooleanField(required=False, initial=False)
    twenty_four_hours = forms.BooleanField(required=False, initial=False)
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
            'placeholder': 'Enter any additional notes about this department...'
        })
    )
    
    class Meta:
        model = HospitalDepartment
        fields = [
            'name',
            'description',
            'phone',
            'email',
            'head_doctor',
            'active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter department name'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
                'placeholder': 'Enter department description'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter phone number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter email address'
            }),
            'head_doctor': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital', None)
        super().__init__(*args, **kwargs)
        
        # Set hospital in instance if not set
        if self.hospital:
            self.instance.hospital = self.hospital
        
        # Add labels
        self.fields['name'].label = 'Department Name *'
        self.fields['description'].label = 'Description *'
        self.fields['phone'].label = 'Department Phone'
        self.fields['email'].label = 'Department Email'
        self.fields['head_doctor'].label = 'Department Head'
        self.fields['active'].label = 'Active'
        
        # Filter head_doctor choices
        if self.hospital:
            from doctors.models import Doctor
            doctors = Doctor.objects.filter(
                hospital=self.hospital,
                is_verified=True,
                is_active=True
            ).select_related('user')
            
            choices = [('', 'Not Assigned')]
            for doctor in doctors:
                display_name = doctor.user.get_full_name() or doctor.user.username
                choices.append((doctor.id, f'Dr. {display_name}'))
            
            self.fields['head_doctor'].choices = choices
    
    def clean_name(self):
        """Validate department name is unique within the hospital."""
        name = self.cleaned_data.get('name')
        if name and self.hospital:
            existing = HospitalDepartment.objects.filter(
                hospital=self.hospital,
                name__iexact=name
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError('A department with this name already exists in your hospital.')
        return name
    
    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone:
            import re
            phone = re.sub(r'[^\d+]', '', phone)
            if len(phone) < 10:
                raise ValidationError('Enter a valid phone number.')
        return phone
    
    def clean_email(self):
        """Validate email format."""
        email = self.cleaned_data.get('email')
        if email:
            from django.core.validators import validate_email
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError('Enter a valid email address.')
        return email
    
    def clean(self):
        """Validate working hours."""
        cleaned_data = super().clean()
        opening_time = cleaned_data.get('opening_time')
        closing_time = cleaned_data.get('closing_time')
        open_24_hours = cleaned_data.get('open_24_hours')
        
        if not open_24_hours and opening_time and closing_time and closing_time <= opening_time:
            raise ValidationError('Closing time must be after opening time.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the form."""
        instance = super().save(commit=False)
        
        if self.hospital and not instance.hospital_id:
            instance.hospital = self.hospital
        
        if commit:
            instance.save()
        
        return instance
    
class RoomForm(forms.ModelForm):
    """Form for creating/editing rooms."""
    
    class Meta:
        model = Room
        fields = [
            'department', 'room_number', 'room_type', 'floor',
            'capacity', 'description', 'status', 'assigned_doctor', 'notes'
        ]
        widgets = {
            'department': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
            }),
            'room_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter room number'
            }),
            'room_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
            }),
            'floor': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter floor number'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter capacity',
                'min': 1
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
                'placeholder': 'Enter room description'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
            }),
            'assigned_doctor': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition appearance-none'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition resize-none',
                'placeholder': 'Enter any additional notes'
            }),
        }
        labels = {
            'department': 'Department',
            'room_number': 'Room Number *',
            'room_type': 'Room Type *',
            'floor': 'Floor',
            'capacity': 'Capacity *',
            'description': 'Description',
            'status': 'Status',
            'assigned_doctor': 'Assigned Doctor',
            'notes': 'Notes',
        }
    
    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital', None)
        super().__init__(*args, **kwargs)
        
        if self.hospital:
            # Filter departments by hospital
            self.fields['department'].queryset = HospitalDepartment.objects.filter(
                hospital=self.hospital,
                active=True
            )
            
            # Filter doctors by hospital
            from doctors.models import Doctor
            self.fields['assigned_doctor'].queryset = Doctor.objects.filter(
                hospital=self.hospital,
                is_active=True
            ).select_related('user')
        
        # Add empty choices
        self.fields['department'].choices = [('', 'Select Department')] + list(self.fields['department'].choices)[1:]
        self.fields['assigned_doctor'].choices = [('', 'Not Assigned')] + list(self.fields['assigned_doctor'].choices)[1:]
    
    def clean_room_number(self):
        """Validate room number uniqueness within hospital."""
        room_number = self.cleaned_data.get('room_number')
        if room_number and self.hospital:
            existing = Room.objects.filter(
                hospital=self.hospital,
                room_number__iexact=room_number
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError('A room with this number already exists in your hospital.')
        return room_number
    
    def clean_capacity(self):
        """Validate capacity."""
        capacity = self.cleaned_data.get('capacity')
        if capacity and capacity < 1:
            raise ValidationError('Capacity must be at least 1.')
        return capacity
    
    def clean_occupied(self):
        """Validate occupied beds don't exceed capacity."""
        occupied = self.cleaned_data.get('occupied', 0)
        capacity = self.cleaned_data.get('capacity', 0)
        if occupied > capacity:
            raise ValidationError('Occupied beds cannot exceed capacity.')
        return occupied
    
    def save(self, commit=True):
        """Save the room."""
        instance = super().save(commit=False)
        if self.hospital:
            instance.hospital = self.hospital
        if commit:
            instance.save()
        return instance
    
class ProfileForm(forms.ModelForm):
    """Form for updating user profile."""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter your email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition',
                'placeholder': 'Enter your phone number'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-500/20 file:text-blue-400 hover:file:bg-blue-500/30'
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'profile_picture': 'Profile Picture',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email required
        self.fields['email'].required = True
    
    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data.get('email')
        if email:
            # Check if email exists for other users
            if User.objects.exclude(id=self.instance.id).filter(email=email).exists():
                raise ValidationError('This email is already registered.')
        return email
    
    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any non-digit characters except +
            phone = re.sub(r'[^\d+]', '', phone)
            # Check if phone number is valid (Bangladesh format)
            if not re.match(r'^\+?8801[3-9]\d{8}$|^01[3-9]\d{8}$', phone):
                raise ValidationError('Enter a valid phone number (e.g., 017XXXXXXXX or +88017XXXXXXXX).')
        return phone
    
    def clean_profile_picture(self):
        """Validate profile picture."""
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Check file size (max 2MB)
            if picture.size > 2 * 1024 * 1024:
                raise ValidationError('Profile picture must be less than 2MB.')
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp']
            ext = picture.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Only JPG, JPEG, PNG, and WEBP files are allowed.')
        return picture


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with validation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition pr-12'
            })
        
        # Add placeholders
        self.fields['old_password'].widget.attrs['placeholder'] = 'Enter your current password'
        self.fields['new_password1'].widget.attrs['placeholder'] = 'Enter your new password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm your new password'
    
    def clean_new_password1(self):
        """Validate new password strength."""
        password = self.cleaned_data.get('new_password1')
        
        if password:
            # Check minimum length
            if len(password) < 8:
                raise ValidationError('Password must be at least 8 characters long.')
            
            # Check uppercase
            if not re.search(r'[A-Z]', password):
                raise ValidationError('Password must contain at least one uppercase letter.')
            
            # Check lowercase
            if not re.search(r'[a-z]', password):
                raise ValidationError('Password must contain at least one lowercase letter.')
            
            # Check digit
            if not re.search(r'\d', password):
                raise ValidationError('Password must contain at least one number.')
            
            # Check special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError('Password must contain at least one special character.')
        
        return password


class NotificationPreferencesForm(forms.Form):
    """Form for notification preferences."""
    
    email_notifications = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )
    sms_notifications = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )
    appointment_notifications = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )
    doctor_verification_notifications = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )
    department_notifications = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )
    system_announcements = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
        })
    )