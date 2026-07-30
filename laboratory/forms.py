# laboratory/forms.py
"""
Django forms for the Laboratory module.

Includes:
- TestCategoryForm
- LaboratoryTestForm
- LabOrderForm (main order with inline items)
- LabOrderItemForm (for inline formset)
- LabResultForm (for uploading results)
- LabOrderItemFormSet (inline formset factory)
"""

from typing import cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from patients.models import Patient

from .models import TestCategory, LaboratoryTest, LabOrder, LabOrderItem, LabResult
from prescriptions.models import Prescription
from appointments.models import Appointment


# ---------- Test Category Form ----------
class TestCategoryForm(forms.ModelForm):
    class Meta:
        model = TestCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-slate-600 text-blue-600 focus:ring-blue-500 '
                         'bg-slate-700',
            }),
        }
        labels = {
            'name': _('Category Name'),
            'description': _('Description'),
            'is_active': _('Active'),
        }


# ---------- Laboratory Test Form ----------
class LaboratoryTestForm(forms.ModelForm):
    class Meta:
        model = LaboratoryTest
        fields = [
            'test_code', 'name', 'category', 'description',
            'normal_range', 'unit', 'sample_type', 'price',
            'preparation', 'is_active'
        ]
        widgets = {
            'test_code': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
                'placeholder': _('e.g., CBC, LFT'),
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm appearance-none',
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
            }),
            'normal_range': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
                'placeholder': _('e.g., 4.5–11.0 x10^3/µL'),
            }),
            'unit': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
                'placeholder': _('e.g., mg/dL, µL'),
            }),
            'sample_type': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
                'placeholder': _('e.g., Blood, Urine'),
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm',
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'preparation': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Special preparation instructions...'),
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-slate-600 text-blue-600 focus:ring-blue-500 '
                         'bg-slate-700',
            }),
        }
        labels = {
            'test_code': _('Test Code'),
            'name': _('Test Name'),
            'category': _('Category'),
            'description': _('Description'),
            'normal_range': _('Normal Range'),
            'unit': _('Unit'),
            'sample_type': _('Sample Type'),
            'price': _('Price (BDT)'),
            'preparation': _('Preparation Instructions'),
            'is_active': _('Active'),
        }
        help_texts = {
            'test_code': _('Short code (e.g., CBC, LFT).'),
            'category': _('Select the test category.'),
            'normal_range': _('e.g., "4.5–11.0 x10^3/µL" or "Male: 13.5–17.5 g/dL".'),
            'price': _('Cost of the test in Bangladeshi Taka.'),
            'is_active': _('Inactive tests will not appear in dropdowns.'),
        }

    def clean_test_code(self):
        code = self.cleaned_data.get('test_code')
        if code:
            code = code.upper().strip()
            qs = LaboratoryTest.objects.filter(test_code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(_('A test with this code already exists.'))
        return code


# ---------- Lab Order Form ----------
class LabOrderForm(forms.ModelForm):
    prescription = forms.ModelChoiceField(
        queryset=Prescription.objects.none(),
        label=_('Prescription'),
        help_text=_('Select a prescription that does not yet have a lab order.'),
    )

    class Meta:
        model = LabOrder
        fields = ['prescription', 'status', 'notes']
        widgets = {
            'prescription': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm appearance-none',
            }),
            'status': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm appearance-none',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Additional notes for lab technician...'),
            }),
        }
        labels = {
            'prescription': _('Prescription'),
            'status': _('Status'),
            'notes': _('Notes'),
        }
        help_texts = {
            'prescription': _('Select a prescription that does not yet have a lab order.'),
            'status': _('Current status of the lab order.'),
            'notes': _('Any special instructions for the lab.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        prescription_field = cast(forms.ModelChoiceField, self.fields['prescription'])

        # Filter prescription queryset to exclude those that already have a lab order
        prescription_qs = Prescription.objects.filter(
            deleted_at__isnull=True
        ).exclude(
            lab_order__isnull=False
        ).select_related(
            'patient', 'doctor', 'hospital', 'appointment',
            'patient__user', 'doctor__user'  # ← important: pre-fetch users
        )

        # If editing an existing order, include its prescription
        if self.instance and self.instance.pk and self.instance.prescription_id:
            prescription_qs = prescription_qs | Prescription.objects.filter(pk=self.instance.prescription.pk)

        prescription_field.queryset = prescription_qs
        prescription_field.label_from_instance = self.prescription_label

    def prescription_label(self, obj):
        """Custom label for prescription dropdown with safe fallbacks."""
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

        return f"{obj.prescription_number} – {patient_name} (Dr. {doctor_name})"

    def clean_prescription(self):
        """Ensure the selected prescription does not already have a lab order."""
        prescription = self.cleaned_data.get('prescription')
        if not prescription:
            return None

        # If updating an existing order, allow the same prescription
        if self.instance and self.instance.pk and self.instance.prescription == prescription:
            return prescription

        # Check if prescription already has an order
        if hasattr(prescription, 'lab_order'):
            raise ValidationError(_('This prescription already has a lab order.'))

        # Ensure appointment is completed (only if appointment exists)
        if prescription.appointment and prescription.appointment.status != 'completed':
            raise ValidationError(_('Prescription must be from a completed appointment.'))

        return prescription


# ---------- Lab Order Item Form (for inline formset) ----------
class LabOrderItemForm(forms.ModelForm):
    test = forms.ModelChoiceField(
        queryset=LaboratoryTest.objects.none(),
        label=_('Test'),
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                     'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                     'transition duration-200 py-2 px-3 text-slate-200 placeholder-slate-400 '
                     'shadow-sm appearance-none',
        }),
    )

    class Meta:
        model = LabOrderItem
        fields = ['test', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-3 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Special instructions for this test...'),
            }),
        }
        labels = {
            'test': _('Test'),
            'notes': _('Notes'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active tests
        test_field = self.fields['test']
        if isinstance(test_field, forms.ModelChoiceField):
            test_field.queryset = LaboratoryTest.objects.filter(
                is_active=True,
                deleted_at__isnull=True
            ).select_related('category')


# ---------- Inline Formset for LabOrder Items ----------
LabOrderItemFormSet = inlineformset_factory(
    LabOrder,
    LabOrderItem,
    form=LabOrderItemForm,
    extra=1,
    min_num=0,
    max_num=20,
    validate_min=False,
    validate_max=True,
    can_delete=True,
)


# ---------- Lab Result Form (for uploading/editing results) ----------
class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ['result', 'interpretation', 'remarks', 'report_file']
        widgets = {
            'result': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Enter the result value (e.g., 5.2, Positive, Normal)'),
            }),
            'interpretation': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Clinical interpretation (e.g., Normal, Abnormal)'),
            }),
            'remarks': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm resize-none',
                'placeholder': _('Additional comments...'),
            }),
            'report_file': forms.ClearableFileInput(attrs={
                'class': 'w-full rounded-xl border border-slate-600 bg-slate-700/50 '
                         'focus:bg-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 '
                         'transition duration-200 py-2 px-4 text-slate-200 placeholder-slate-400 '
                         'shadow-sm file:bg-slate-600 file:border-0 file:text-white file:cursor-pointer '
                         'file:rounded-xl file:px-4 file:py-2 file:mr-4',
            }),
        }
        labels = {
            'result': _('Result'),
            'interpretation': _('Interpretation'),
            'remarks': _('Remarks'),
            'report_file': _('Report File'),
        }
        help_texts = {
            'result': _('Enter the actual result value or description.'),
            'interpretation': _('Interpretation of the result (Normal, Abnormal, etc.).'),
            'report_file': _('Upload PDF, JPEG, or PNG file (max 10 MB).'),
        }

    def clean_result(self):
        result = self.cleaned_data.get('result')
        if result and len(result.strip()) < 1:
            raise ValidationError(_('Result cannot be empty.'))
        return result

    def clean_report_file(self):
        file = self.cleaned_data.get('report_file')
        if file:
            ext = file.name.split('.')[-1].lower()
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            if ext not in allowed_extensions:
                raise ValidationError(_('Only PDF, JPEG, and PNG files are allowed.'))
            if file.size > 10 * 1024 * 1024:
                raise ValidationError(_('File size must be under 10 MB.'))
        return file
    
class DoctorLabRequestForm(forms.ModelForm):
    """Form for doctors to create laboratory requests."""
    
    # ✅ শুধু tests এবং notes ফিল্ড রাখুন
    # বাকি সব ফিল্ড auto-populated হবে
    
    tests = forms.ModelMultipleChoiceField(
        queryset=LaboratoryTest.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'test-checkbox-grid',
        }),
        label='Requested Laboratory Tests',
        help_text='Select at least one test'
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('normal', 'Normal'),
            ('urgent', 'Urgent'),
            ('emergency', 'Emergency'),
        ],
        initial='normal',
        widget=forms.Select(attrs={
            'class': 'form-input',
        }),
        label='Priority'
    )
    
    diagnosis = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Enter the clinical diagnosis...',
        }),
        label='Clinical Diagnosis',
        help_text='Required. Provide the diagnosis for this lab request'
    )
    
    clinical_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Enter any clinical notes (optional)...',
        }),
        label='Clinical Notes',
        required=False,
        help_text='Optional additional clinical information'
    )
    
    instructions = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 2,
            'placeholder': 'Any special instructions for sample collection (optional)...',
        }),
        label='Additional Instructions',
        required=False,
        help_text='Optional instructions for laboratory staff'
    )
    
    class Meta:
        model = LabOrder
        # ✅ শুধু notes ফিল্ড রাখুন (বাকি সব auto-populated)
        fields = ['tests', 'priority', 'diagnosis', 'clinical_notes', 'instructions', 'notes']
        widgets = {
            'notes': forms.HiddenInput(),  # Hidden field, will be set in view
        }
    
    def __init__(self, doctor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doctor = doctor
    
    def clean(self):
        cleaned_data = super().clean()
        tests = cleaned_data.get('tests')
        diagnosis = cleaned_data.get('diagnosis', '').strip()
        
        # Validate diagnosis
        if not diagnosis:
            raise ValidationError("Clinical Diagnosis is required.")
        
        if len(diagnosis) < 5:
            raise ValidationError("Diagnosis must be at least 5 characters.")
        
        # Validate at least one test selected
        if not tests:
            raise ValidationError("At least one laboratory test must be selected.")
        
        return cleaned_data