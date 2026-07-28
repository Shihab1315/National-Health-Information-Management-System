from django import forms
from .models import Hospital, HospitalDepartment, HospitalFacility, HospitalGallery, HospitalOperatingHour
from .validators import validate_phone, validate_email, validate_website


class HospitalForm(forms.ModelForm):
    class Meta:
        model = Hospital
        fields = [
            # Basic
            'name', 'registration_number', 'license_number', 'tin', 'bin',
            'hospital_type', 'ownership', 'established_year',
            # Description
            'description', 'short_description', 'mission', 'vision', 'history',
            # Logo & Cover
            'logo', 'cover_image',
            # Address
            'country', 'division', 'district', 'upazila', 'city', 'area',
            'postal_code', 'full_address', 'latitude', 'longitude', 'google_map_link',
            # Contact
            'email', 'phone', 'emergency_phone', 'ambulance_phone', 'website',
            # Social
            'facebook', 'linkedin', 'twitter', 'instagram', 'youtube',
            # Facilities
            'emergency_available', 'icu', 'nicu', 'ccu', 'emergency_department',
            'operation_theater', 'laboratory', 'radiology', 'mri', 'ct_scan',
            'x_ray', 'ultrasound', 'blood_bank', 'pharmacy', 'vaccination_center',
            'dialysis', 'cancer_unit', 'burn_unit', 'heart_center', 'eye_center',
            'dental_unit',
            # Amenities
            'parking', 'wheelchair_access', 'prayer_room', 'cafeteria',
            'atm', 'wifi', 'generator_backup', 'oxygen_plant', 'open_24_hours',
            # Statistics
            'total_doctors', 'total_nurses', 'total_beds',
            'available_beds', 'icu_beds', 'emergency_beds',
            # Status
            'verified', 'featured', 'active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'mission': forms.Textarea(attrs={'rows': 3}),
            'vision': forms.Textarea(attrs={'rows': 3}),
            'history': forms.Textarea(attrs={'rows': 4}),
            'full_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.Select)):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 outline-none transition'
                })
        # Override for selects and checkboxes
        for field_name in ['hospital_type', 'ownership', 'country', 'division', 'district', 'upazila', 'city']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white focus:border-emerald-500 outline-none transition'
                })
        # Checkbox styling
        for field_name in [
            'emergency_available', 'icu', 'nicu', 'ccu', 'emergency_department',
            'operation_theater', 'laboratory', 'radiology', 'mri', 'ct_scan',
            'x_ray', 'ultrasound', 'blood_bank', 'pharmacy', 'vaccination_center',
            'dialysis', 'cancer_unit', 'burn_unit', 'heart_center', 'eye_center',
            'dental_unit', 'parking', 'wheelchair_access', 'prayer_room', 'cafeteria',
            'atm', 'wifi', 'generator_backup', 'oxygen_plant', 'open_24_hours',
            'verified', 'featured', 'active'
        ]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-emerald-500 focus:ring-emerald-500'
                })


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = HospitalDepartment
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 outline-none transition'
                })


class FacilityForm(forms.ModelForm):
    class Meta:
        model = HospitalFacility
        fields = '__all__'


class GalleryForm(forms.ModelForm):
    class Meta:
        model = HospitalGallery
        fields = '__all__'


class OperatingHourForm(forms.ModelForm):
    class Meta:
        model = HospitalOperatingHour
        fields = '__all__'