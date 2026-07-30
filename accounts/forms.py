from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re
User = get_user_model()
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate

class SignupForm(forms.ModelForm):
    """
    Production-ready signup form with role selection and validation.
    """
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('hospital_admin', 'Hospital Admin'),
    )
    
    # Password fields
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter password',
            'autocomplete': 'new-password',
        }),
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password',
        }),
        label='Confirm Password'
    )
    
    # Role selection
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'role-select',
        }),
        label='I want to register as'
    )
    
    # Terms agreement
    agree_terms = forms.BooleanField(
        required=True,
        label='I agree to the Terms & Conditions and Privacy Policy',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        })
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email', 'phone',  # ✅ phone ব্যবহার করুন (phone_number নয়)
            'role', 'password', 'confirm_password', 'agree_terms'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your first name',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your last name',
                'autocomplete': 'family-name',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Choose a username',
                'autocomplete': 'username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your email address',
                'autocomplete': 'email',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your phone number (e.g., 017XXXXXXXX)',
                'autocomplete': 'tel',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['phone'].required = True
        self.fields['role'].required = True
    
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken.')
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already registered.')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            # Bangladesh phone number validation
            if not re.match(r'^01[3-9]\d{8}$', phone):
                raise ValidationError('Enter a valid Bangladesh phone number (e.g., 017XXXXXXXX)')
        return phone
    
    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters.')
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = self.cleaned_data['role']
        user.is_active = True
        
        if commit:
            user.save()
        
        return user


class LoginForm(AuthenticationForm):
    """
    Custom login form with improved validation and UX.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username or Email',
            'autocomplete': 'username',
            'autofocus': True,
        }),
        label='Username or Email'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        }),
        label='Password'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
        }),
        label='Remember Me'
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Authenticate user
            user = authenticate(
                self.request,
                username=username,
                password=password
            )
            
            if user is None:
                raise ValidationError('Invalid username/email or password.')
            
            if not user.is_active:
                raise ValidationError('Your account is inactive. Please contact administrator.')
            
            # Check if account is disabled
            if hasattr(user, 'is_disabled') and user.is_disabled:
                raise ValidationError('Your account has been disabled. Please contact administrator.')
            
            # Set user in cleaned data
            self.user_cache = user
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user_cache
class UserEditForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'nid', 'profile_picture', 'role', 'hospital')