# appointments/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from typing import cast

from .models import Appointment
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient


class AppointmentForm(forms.ModelForm):
    """
    Form for creating and updating appointments.
    Includes custom validation for date, time, doctor availability,
    and consistency between hospital, doctor, and patient.
    """

    appointment_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
                'placeholder': 'Select appointment date',
            }
        ),
        label=_('Appointment Date'),
        help_text=_('Select a date for the appointment.'),
    )

    appointment_time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={
                'type': 'time',
                'class': 'form-control',
                'placeholder': 'Select appointment time',
            }
        ),
        label=_('Appointment Time'),
        help_text=_('Choose the time for the appointment.'),
    )

    class Meta:
        model = Appointment
        fields = [
            'hospital', 'doctor', 'patient',
            'appointment_date', 'appointment_time',
            'reason', 'status',
        ]
        widgets = {
            'hospital': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief reason for the appointment',
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'hospital': _('Hospital'),
            'doctor': _('Doctor'),
            'patient': _('Patient'),
            'reason': _('Reason'),
            'status': _('Status'),
        }
        help_texts = {
            'hospital': _('Select the hospital where the appointment will take place.'),
            'doctor': _('Choose the doctor for this appointment.'),
            'patient': _('Select the patient.'),
            'status': _('Current status of the appointment.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Querysets with ordering for better UX
        hospital_qs = Hospital.objects.filter(is_deleted=False).order_by('name')
        doctor_qs = Doctor.objects.filter(is_active=True).order_by('full_name', 'user__first_name')
        patient_qs = Patient.objects.filter(is_active=True).order_by('user__first_name', 'user__last_name')

        if self.instance and self.instance.pk:
            hospital = self.instance.hospital
            if hospital and not hospital_qs.filter(pk=hospital.pk).exists():
                hospital_qs = hospital_qs | Hospital.objects.filter(pk=hospital.pk)

            doctor = self.instance.doctor
            if doctor and not doctor_qs.filter(pk=doctor.pk).exists():
                doctor_qs = doctor_qs | Doctor.objects.filter(pk=doctor.pk)

            patient = self.instance.patient
            if patient and not patient_qs.filter(pk=patient.pk).exists():
                patient_qs = patient_qs | Patient.objects.filter(pk=patient.pk)

        # assign querysets with casts to satisfy static type checkers
        cast(forms.ModelChoiceField, self.fields['hospital']).queryset = hospital_qs
        cast(forms.ModelChoiceField, self.fields['doctor']).queryset = doctor_qs
        cast(forms.ModelChoiceField, self.fields['patient']).queryset = patient_qs

        # ★★★ Custom labels for dropdown options ★★★
        cast(forms.ModelChoiceField, self.fields['doctor']).label_from_instance = self.get_doctor_label
        cast(forms.ModelChoiceField, self.fields['patient']).label_from_instance = self.get_patient_label

    def get_doctor_label(self, obj):
        """
        ডাক্তারের জন্য ড্রপডাউনের লেবেল তৈরি করে।
        - নাম: full_name অথবা user.get_full_name() অথবা user.username
        - আইডি: doctor_id (DOC-XXXXX) অথবা pk
        """
        # ১. নাম নির্ধারণ
        if obj.full_name and obj.full_name != 'Unknown':
            name = obj.full_name
        elif obj.user and obj.user.get_full_name():
            name = obj.user.get_full_name()
        elif obj.user and obj.user.username:
            name = obj.user.username
        else:
            name = 'Doctor'  # ফ্যালব্যাক

        # ২. আইডেন্টিফায়ার – doctor_id (DOC-XXXXX) অথবা pk
        identifier = obj.doctor_id if obj.doctor_id else str(obj.pk)

        return f"Dr. {name} ({identifier})"

    def get_patient_label(self, obj):
        """পেশেন্টের জন্য ড্রপডাউনের লেবেল তৈরি করে।"""
        if hasattr(obj, 'full_name') and obj.full_name:
            return obj.full_name
        elif obj.user:
            return obj.user.get_full_name() or obj.user.username
        else:
            return f"Patient-{obj.pk}"

    def clean_appointment_date(self):
        date = self.cleaned_data.get('appointment_date')
        if date and date < timezone.now().date():
            raise ValidationError(
                _('Appointment date cannot be in the past. Please select a future date.')
            )
        return date

    def clean(self):
        """
        Perform cross‑field validation:
        1. Ensure the doctor belongs to the selected hospital.
        2. Ensure patient is active.
        The overlapping appointment check is handled in the model's clean().
        """
        cleaned_data = super().clean()
        hospital = cleaned_data.get('hospital')
        doctor = cleaned_data.get('doctor')
        patient = cleaned_data.get('patient')

        # 1. Hospital – Doctor relationship validation
        if hospital and doctor:
            if doctor.hospital != hospital:
                raise ValidationError(
                    _('The selected doctor does not belong to the chosen hospital. '
                      'Please select a doctor from the chosen hospital.')
                )

        # 2. Ensure patient is active (if the model has an 'is_active' flag)
        if patient and hasattr(patient, 'is_active') and not patient.is_active:
            raise ValidationError(_('The selected patient is inactive.'))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance
class PatientAppointmentForm(forms.ModelForm):
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-blue-500 outline-none'})
    )
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-blue-500 outline-none'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-blue-500 outline-none'})
    )

    class Meta:
        model = Appointment
        fields = ['hospital', 'doctor', 'appointment_date', 'appointment_time', 'reason']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter hospitals: not deleted and active
        self.fields['hospital'].queryset = Hospital.objects.filter(is_deleted=False, active=True)
        # Filter doctors: active only
        self.fields['doctor'].queryset = Doctor.objects.filter(is_active=True)

        # Apply Tailwind classes to all fields (if not already set via widget attrs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-blue-500 outline-none'