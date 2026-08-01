# hospital_admin/forms.py
from django import forms
from django.core.exceptions import ValidationError
from hospitals.models import HospitalApplication
import re

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