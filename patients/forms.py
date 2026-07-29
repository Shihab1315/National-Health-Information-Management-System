from django import forms
from .models import Patient, PatientSettings


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            # Personal & contact
            'national_id', 'full_name', 'date_of_birth', 'gender', 'blood_group',
            'marital_status', 'phone', 'email', 'address', 'city', 'district',
            'zip_code', 'allergies', 'chronic_diseases',
            # Emergency contact
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_relationship', 'emergency_alt_phone', 'emergency_email',
            'emergency_address',
            'secondary_contact_name', 'secondary_contact_relationship',
            'secondary_contact_phone', 'secondary_contact_email',
            'is_medical_decision_maker', 'preferred_ambulance',
            # Medical information (permanent)
            'height', 'weight', 'bmi',
            'smoking_status', 'alcohol_consumption', 'exercise_frequency',
            'diet_preference',
             # INSURANCE FIELDS
            'has_insurance', 'insurance_provider', 'insurance_plan', 'policy_number',
            'member_id', 'insurance_type', 'coverage_amount', 'coverage_start_date',
            'coverage_end_date', 'coverage_percentage', 'emergency_coverage_available',
            'cashless_facility', 'insurance_notes',
            # ... profile_photo at the end ...
            # Profile photo
            'profile_photo'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'chronic_diseases': forms.Textarea(attrs={'rows': 2}),
            'emergency_address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply common styling to all fields
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 transition outline-none'
                })

        # Select fields (including lifestyle choices)
        select_fields = [
            'gender', 'blood_group', 'marital_status',
            'smoking_status', 'alcohol_consumption',
            'exercise_frequency', 'diet_preference'
        ]
        for field_name in select_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white focus:border-blue-500'
                })

        # Checkbox for medical decision maker
        if 'is_medical_decision_maker' in self.fields:
            self.fields['is_medical_decision_maker'].widget.attrs.update({
                'class': 'w-5 h-5 text-blue-600 focus:ring-blue-500 focus:ring-2 rounded border-white/10 bg-white/5'
            })

        # BMI is read-only
        if 'bmi' in self.fields:
            self.fields['bmi'].widget.attrs.update({
                'readonly': 'readonly',
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 transition outline-none opacity-70'
            })

    def clean(self):
        cleaned_data = super().clean()
        height = cleaned_data.get('height')
        weight = cleaned_data.get('weight')
        if height and weight:
            height_m = height / 100
            bmi = round(weight / (height_m * height_m), 2)
            cleaned_data['bmi'] = bmi
        else:
            cleaned_data['bmi'] = None
        return cleaned_data
    
class PatientSettingsForm(forms.ModelForm):
    class Meta:
        model = PatientSettings
        exclude = ['patient', 'updated_at']
        widgets = {
            'appearance': forms.RadioSelect(choices=PatientSettings.APPEARANCE_CHOICES),
            'language': forms.Select(choices=PatientSettings.LANGUAGE_CHOICES),
            'notify_appointments': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'notify_prescriptions': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'notify_laboratory': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'notify_system': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'show_mobile': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'show_email': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'hide_personal_info': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'large_font': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'high_contrast': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
            'reduced_motion': forms.CheckboxInput(attrs={'class': 'toggle-checkbox sr-only'}),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        # If we have an instance and this is a GET (no POST data), set initial from instance
        if instance and not kwargs.get('data'):
            kwargs['initial'] = {
                'appearance': instance.appearance,
                'language': instance.language,
                'notify_appointments': instance.notify_appointments,
                'notify_prescriptions': instance.notify_prescriptions,
                'notify_laboratory': instance.notify_laboratory,
                'notify_system': instance.notify_system,
                'show_mobile': instance.show_mobile,
                'show_email': instance.show_email,
                'hide_personal_info': instance.hide_personal_info,
                'large_font': instance.large_font,
                'high_contrast': instance.high_contrast,
                'reduced_motion': instance.reduced_motion,
            }
        super().__init__(*args, **kwargs)