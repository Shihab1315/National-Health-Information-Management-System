# doctors/forms.py
from django import forms
from .models import Doctor, Specialty

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