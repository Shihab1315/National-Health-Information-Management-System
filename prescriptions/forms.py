# prescriptions/forms.py
"""
Forms for the Prescription module.

Includes main prescription form and inline formset for medicines.
Handles validation, auto‑population from appointment, and Tailwind‑ready widgets.
"""

from typing import cast
from django.forms import inlineformset_factory

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Prescription, PrescriptionMedicine
from appointments.models import Appointment


class PrescriptionForm(forms.ModelForm):
    """
    Main form for creating/updating a prescription.
    Appointment is the only selection field – hospital, doctor, patient are auto‑populated.
    """

    appointment = forms.ModelChoiceField(
        queryset=Appointment.objects.filter(
            status=Appointment.Status.COMPLETED,
            deleted_at__isnull=True,
            prescription__isnull=True  # only appointments without a prescription
        ).select_related('patient', 'doctor', 'hospital', 'patient__user', 'doctor__user'),
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                     'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                     'transition duration-200 py-3 pl-4 pr-8 text-slate-200 placeholder-slate-400 '
                     'shadow-sm appearance-none',
        }),
        label=_('Appointment'),
        help_text=_('Select a completed appointment that does not yet have a prescription.'),
        empty_label=_('Select a completed appointment'),
        required=True,
    )

    class Meta:
        model = Prescription
        fields = [
            'appointment',
            'diagnosis',
            'symptoms',
            'clinical_notes',
            'advice',
            'follow_up_date',
            'status',
        ]
        widgets = {
            'diagnosis': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-3 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Enter the diagnosis...'),
            }),
            'symptoms': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-3 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('List the symptoms...'),
            }),
            'clinical_notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-3 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Additional clinical notes...'),
            }),
            'advice': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-3 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Advice and recommendations...'),
            }),
            'follow_up_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-3 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
            }),
            'status': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-3 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm appearance-none',
            }),
        }
        labels = {
            'appointment': _('Appointment'),
            'diagnosis': _('Diagnosis'),
            'symptoms': _('Symptoms'),
            'clinical_notes': _('Clinical Notes'),
            'advice': _('Advice'),
            'follow_up_date': _('Follow-up Date'),
            'status': _('Status'),
        }
        help_texts = {
            'diagnosis': _('Medical diagnosis based on the appointment.'),
            'symptoms': _('Symptoms reported by the patient.'),
            'clinical_notes': _('Additional observations and notes.'),
            'advice': _('General advice and recommendations for the patient.'),
            'follow_up_date': _('Scheduled follow‑up date, if any.'),
            'status': _('Current status of the prescription.'),
        }

    def __init__(self, *args, **kwargs):
        # Allow passing a filtered appointment queryset from the view
        self.appointment_queryset = kwargs.pop('appointment_queryset', None)
        super().__init__(*args, **kwargs)

        appointment_field = cast(forms.ModelChoiceField, self.fields['appointment'])

        if self.appointment_queryset is not None:
            appointment_field.queryset = self.appointment_queryset

        # Custom label for appointment choices
        appointment_field.label_from_instance = self.appointment_label

    def appointment_label(self, obj):
        """Custom label for the appointment dropdown with safe fallbacks."""
        # Patient name
        patient_name = "N/A"
        if obj.patient:
            if obj.patient.user:
                patient_name = obj.patient.user.get_full_name() or obj.patient.user.username
            elif obj.patient.full_name:
                patient_name = obj.patient.full_name

        # Doctor name
        doctor_name = "N/A"
        if obj.doctor:
            if obj.doctor.user:
                doctor_name = obj.doctor.user.get_full_name() or obj.doctor.user.username
            elif obj.doctor.full_name:
                doctor_name = obj.doctor.full_name

        return f"{obj.appointment_number} – {patient_name} with Dr. {doctor_name} on {obj.appointment_date}"

    def clean_appointment(self):
        """Validate that the selected appointment is eligible for a prescription."""
        appointment = self.cleaned_data.get('appointment')
        if not appointment:
            return None

        # 1. Appointment must be completed
        if appointment.status != Appointment.Status.COMPLETED:
            raise ValidationError(
                _('Prescription can only be created for a completed appointment.')
            )

        # 2. Check for existing prescription (if not updating)
        if not self.instance.pk and hasattr(appointment, 'prescription'):
            raise ValidationError(
                _('A prescription already exists for this appointment.')
            )

        # 3. Ensure the appointment has a patient and doctor (should be required by model)
        if not appointment.patient:
            raise ValidationError(_('The selected appointment has no patient.'))
        if not appointment.doctor:
            raise ValidationError(_('The selected appointment has no doctor.'))

        return appointment

    def clean_follow_up_date(self):
        """Ensure follow‑up date is in the future."""
        date = self.cleaned_data.get('follow_up_date')
        if date and date < timezone.now().date():
            raise ValidationError(_('Follow‑up date cannot be in the past.'))
        return date

    def clean(self):
        """
        Cross‑field validation: ensure that if status is Issued or Completed,
        required fields like diagnosis are filled.
        """
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        diagnosis = cleaned_data.get('diagnosis')

        if status in (Prescription.Status.ISSUED, Prescription.Status.COMPLETED):
            if not diagnosis:
                self.add_error('diagnosis', _('Diagnosis is required when issuing or completing a prescription.'))

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to set created_by/updated_by and auto‑populate fields.
        However, the model's save() already handles auto‑populate,
        so we just set the audit user if needed.
        """
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
        return instance



    
class PrescriptionMedicineForm(forms.ModelForm):
    """Form for individual prescription medicines with validation."""
    
    class Meta:
        model = PrescriptionMedicine
        fields = [
            'medicine_name', 'dosage', 'frequency', 'duration',
            'route', 'instruction', 'notes',
            'before_food', 'after_food', 'morning', 'afternoon', 'night'
        ]
        widgets = {
            'medicine_name': forms.TextInput(attrs={
                'class': 'form-input medicine-input',
                'placeholder': 'Enter medicine name *',
            }),
            'dosage': forms.TextInput(attrs={
                'class': 'form-input medicine-input',
                'placeholder': 'e.g., 500mg *',
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-input medicine-input',
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-input medicine-input',
                'placeholder': 'e.g., 7 days *',
            }),
            'route': forms.Select(attrs={
                'class': 'form-input medicine-input',
            }),
            'instruction': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Special instructions (optional)',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Additional notes (optional)',
            }),
            'before_food': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'after_food': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'morning': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'afternoon': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'night': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }
    
    def clean_medicine_name(self):
        medicine_name = self.cleaned_data.get('medicine_name', '').strip()
        if not medicine_name:
            raise ValidationError("Medicine name is required.")
        if len(medicine_name) < 2:
            raise ValidationError("Medicine name must be at least 2 characters.")
        return medicine_name
    
    def clean_dosage(self):
        dosage = self.cleaned_data.get('dosage', '').strip()
        if not dosage:
            raise ValidationError("Dosage is required.")
        return dosage
    
    def clean_duration(self):
        duration = self.cleaned_data.get('duration', '').strip()
        if not duration:
            raise ValidationError("Duration is required.")
        return duration


class PrescriptionEditForm(forms.ModelForm):
    """Form for editing prescriptions with validation."""
    
    class Meta:
        model = Prescription
        fields = [
            'diagnosis', 'symptoms', 'clinical_notes',
            'advice', 'follow_up_date'
        ]
        widgets = {
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Enter the diagnosis...',
            }),
            'symptoms': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Enter the symptoms reported...',
            }),
            'clinical_notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Enter clinical notes...',
            }),
            'advice': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Provide advice and recommendations...',
            }),
            'follow_up_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['diagnosis'].required = True
    
    def clean_diagnosis(self):
        diagnosis = self.cleaned_data.get('diagnosis', '').strip()
        if not diagnosis:
            raise ValidationError("Diagnosis is required.")
        if len(diagnosis) < 10:
            raise ValidationError("Diagnosis must be at least 10 characters.")
        if len(diagnosis) > 3000:
            raise ValidationError("Diagnosis cannot exceed 3000 characters.")
        return diagnosis
    
    def clean_advice(self):
        advice = self.cleaned_data.get('advice', '').strip()
        if len(advice) > 2000:
            raise ValidationError("Advice cannot exceed 2000 characters.")
        return advice
    
    def clean_follow_up_date(self):
        follow_up_date = self.cleaned_data.get('follow_up_date')
        if follow_up_date and follow_up_date < timezone.now().date():
            raise ValidationError("Follow-up date cannot be in the past.")
        return follow_up_date
    
    def clean_symptoms(self):
        symptoms = self.cleaned_data.get('symptoms', '').strip()
        if symptoms:
            lines = [line.strip() for line in symptoms.split('\n') if line.strip()]
            return '\n'.join(lines)
        return ''


# Create inline formset for medicines
PrescriptionMedicineFormSet = inlineformset_factory(
    Prescription,
    PrescriptionMedicine,
    form=PrescriptionMedicineForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
    max_num=20,
    validate_max=True,
)


class PrescriptionCreateForm(forms.ModelForm):
    """Form for creating prescriptions with validation."""
    
    class Meta:
        model = Prescription
        fields = [
            'diagnosis', 'symptoms', 'clinical_notes',
            'advice', 'follow_up_date'
        ]
        widgets = {
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Enter the diagnosis...',
            }),
            'symptoms': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Enter the symptoms reported...',
            }),
            'clinical_notes': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Enter clinical notes...',
            }),
            'advice': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Provide advice and recommendations...',
            }),
            'follow_up_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input',
            }),
        }
    
    def clean_diagnosis(self):
        diagnosis = self.cleaned_data.get('diagnosis', '').strip()
        if not diagnosis:
            raise ValidationError("Diagnosis is required.")
        if len(diagnosis) < 10:
            raise ValidationError("Diagnosis must be at least 10 characters.")
        if len(diagnosis) > 3000:
            raise ValidationError("Diagnosis cannot exceed 3000 characters.")
        return diagnosis
    
    def clean_advice(self):
        advice = self.cleaned_data.get('advice', '').strip()
        if len(advice) > 2000:
            raise ValidationError("Advice cannot exceed 2000 characters.")
        return advice
    
    def clean_follow_up_date(self):
        follow_up_date = self.cleaned_data.get('follow_up_date')
        if follow_up_date and follow_up_date < timezone.now().date():
            raise ValidationError("Follow-up date cannot be in the past.")
        return follow_up_date
    
    def clean_symptoms(self):
        symptoms = self.cleaned_data.get('symptoms', '').strip()
        if symptoms:
            lines = [line.strip() for line in symptoms.split('\n') if line.strip()]
            return '\n'.join(lines)
        return ''