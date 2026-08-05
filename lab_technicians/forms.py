from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import LabTechnician

User = get_user_model()

class CreateLabTechnicianForm(forms.ModelForm):
    """
    Form for Hospital Admin to create Lab Technician accounts.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = LabTechnician
        fields = [
            'full_name',
            'phone',
            'department',
            'profile_photo',
            'is_active',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter department (e.g., Pathology, Radiology)'
            }),
            'profile_photo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data

    def save(self, hospital, commit=True):
        """
        Save the form data creating both User and LabTechnician.
        """
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            role='lab_technician'
        )

        lab_technician = super().save(commit=False)
        lab_technician.user = user
        lab_technician.hospital = hospital

        if commit:
            lab_technician.save()

        return lab_technician


class EditLabTechnicianForm(forms.ModelForm):
    """
    Form for Hospital Admin to edit Lab Technician accounts.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )

    class Meta:
        model = LabTechnician
        fields = [
            'full_name',
            'phone',
            'department',
            'profile_photo',
            'is_active',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter department'
            }),
            'profile_photo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        instance = self.instance
        if User.objects.filter(email=email).exclude(id=instance.user.id).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        lab_technician = super().save(commit=False)
        
        # Update user email
        user = lab_technician.user
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            lab_technician.save()

        return lab_technician