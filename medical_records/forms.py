from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import MedicalRecord, Allergy, ChronicDisease, PastHistory, Vaccination, FollowUp, Attachment


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            'patient', 'doctor', 'hospital', 'appointment', 'prescription', 'lab_order',
            'visit_date', 'chief_complaint', 'symptoms', 'history_of_present_illness',
            'diagnosis', 'clinical_findings',
            'blood_pressure_systolic', 'blood_pressure_diastolic', 'pulse',
            'temperature', 'height', 'weight', 'bmi', 'oxygen_saturation', 'respiratory_rate',
            'treatment_plan', 'doctor_notes', 'follow_up_date', 'status'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'chief_complaint': forms.Textarea(attrs={'rows': 3}),
            'symptoms': forms.Textarea(attrs={'rows': 2}),
            'history_of_present_illness': forms.Textarea(attrs={'rows': 4}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'clinical_findings': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'doctor_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition'
                })
        for field_name in ['patient', 'doctor', 'hospital', 'appointment', 'prescription', 'lab_order', 'status']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-[#0d2137] border border-white/10 text-white focus:border-blue-500 outline-none transition'
                })

    def clean(self):
        """
        Validate field consistency.
        - Follow‑up date cannot be before visit date.
        - Blood pressure: systolic > diastolic.
        - Pulse, temperature, oxygen saturation, respiratory rate within reasonable ranges.
        """
        cleaned_data = super().clean()
        visit_date = cleaned_data.get('visit_date')
        follow_up_date = cleaned_data.get('follow_up_date')
        sys = cleaned_data.get('blood_pressure_systolic')
        dia = cleaned_data.get('blood_pressure_diastolic')
        pulse = cleaned_data.get('pulse')
        temp = cleaned_data.get('temperature')
        oxygen = cleaned_data.get('oxygen_saturation')
        resp = cleaned_data.get('respiratory_rate')

        if visit_date and follow_up_date and follow_up_date < visit_date.date():
            self.add_error('follow_up_date', _('Follow‑up date cannot be before visit date.'))

        if sys and dia and sys <= dia:
            self.add_error('blood_pressure_systolic', _('Systolic blood pressure must be higher than diastolic.'))

        if pulse and (pulse < 30 or pulse > 200):
            self.add_error('pulse', _('Pulse must be between 30 and 200 bpm.'))

        if temp and (temp < 95 or temp > 105):
            self.add_error('temperature', _('Temperature must be between 95 and 105 °F.'))

        if oxygen and (oxygen < 0 or oxygen > 100):
            self.add_error('oxygen_saturation', _('Oxygen saturation must be between 0 and 100%.'))

        if resp and (resp < 5 or resp > 40):
            self.add_error('respiratory_rate', _('Respiratory rate must be between 5 and 40 breaths per minute.'))

        return cleaned_data


class AllergyForm(forms.ModelForm):
    class Meta:
        model = Allergy
        fields = '__all__'
        widgets = {
            'reaction': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 outline-none transition'
            })


class ChronicDiseaseForm(forms.ModelForm):
    class Meta:
        model = ChronicDisease
        fields = '__all__'


class PastHistoryForm(forms.ModelForm):
    class Meta:
        model = PastHistory
        fields = '__all__'
        widgets = {
            'surgeries': forms.Textarea(attrs={'rows': 2}),
            'hospital_admissions': forms.Textarea(attrs={'rows': 2}),
            'family_history': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class VaccinationForm(forms.ModelForm):
    class Meta:
        model = Vaccination
        fields = '__all__'
        widgets = {
            'administration_date': forms.DateInput(attrs={'type': 'date'}),
            'next_due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        admin_date = cleaned_data.get('administration_date')
        next_due = cleaned_data.get('next_due_date')

        if admin_date and next_due and next_due < admin_date:
            self.add_error('next_due_date', _('Next due date cannot be before administration date.'))

        return cleaned_data


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = '__all__'
        widgets = {
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'completed_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        scheduled = cleaned_data.get('scheduled_date')
        completed = cleaned_data.get('completed_date')

        if scheduled and completed and completed < scheduled:
            self.add_error('completed_date', _('Completed date cannot be before scheduled date.'))

        return cleaned_data


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['file', 'description']

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            allowed = ['pdf', 'jpg', 'jpeg', 'png']
            if ext not in allowed:
                raise ValidationError(_('Only PDF, JPEG, and PNG files are allowed.'))
        return file