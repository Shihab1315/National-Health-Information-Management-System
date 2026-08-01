# superadmin/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordChangeForm
import re
import os

User = get_user_model()


class SuperAdminProfileForm(forms.ModelForm):
    """Form for Super Admin profile update."""
    
    class Meta:
        model = User
        fields = ['profile_picture', 'first_name', 'last_name', 'email', 'phone']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field, forms.FileField):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-500/20 file:text-blue-400 hover:file:bg-blue-500/30'
                })
            elif isinstance(field, forms.BooleanField):
                field.widget.attrs.update({
                    'class': 'w-4 h-4 rounded border-white/10 bg-white/5 text-blue-500 focus:ring-blue-500'
                })
            else:
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition'
                })
        
        # Add placeholders
        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter your first name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter your last name'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter your email address'
        self.fields['phone'].widget.attrs['placeholder'] = 'Enter your phone number'
    
    def clean_profile_picture(self):
        """Validate profile picture."""
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Check file size (max 2MB)
            if picture.size > 2 * 1024 * 1024:
                raise ValidationError('Profile picture must be less than 2MB.')
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png']
            ext = picture.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Only JPG, JPEG, and PNG files are allowed.')
        
        return picture
    
    def clean_phone(self):
        """Validate phone number."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any non-digit characters except +
            phone = re.sub(r'[^\d+]', '', phone)
            
            # Check if phone number is valid (Bangladesh format)
            if not re.match(r'^\+?8801[3-9]\d{8}$|^01[3-9]\d{8}$', phone):
                raise ValidationError('Enter a valid phone number (e.g., 017XXXXXXXX or +88017XXXXXXXX).')
        
        return phone
    
    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data.get('email')
        if email:
            # Check if email exists for other users
            if User.objects.exclude(id=self.instance.id).filter(email=email).exists():
                raise ValidationError('This email is already registered.')
        return email


class SuperAdminPasswordChangeForm(PasswordChangeForm):
    """Form for Super Admin password change."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition pr-12'
            })
        
        # Add placeholders
        self.fields['old_password'].widget.attrs['placeholder'] = 'Enter your current password'
        self.fields['new_password1'].widget.attrs['placeholder'] = 'Enter your new password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm your new password'
    
    def clean_new_password1(self):
        """Validate new password strength."""
        password = self.cleaned_data.get('new_password1')
        
        if password:
            # Check minimum length
            if len(password) < 8:
                raise ValidationError('Password must be at least 8 characters long.')
            
            # Check uppercase
            if not re.search(r'[A-Z]', password):
                raise ValidationError('Password must contain at least one uppercase letter.')
            
            # Check lowercase
            if not re.search(r'[a-z]', password):
                raise ValidationError('Password must contain at least one lowercase letter.')
            
            # Check digit
            if not re.search(r'\d', password):
                raise ValidationError('Password must contain at least one number.')
            
            # Check special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError('Password must contain at least one special character.')
        
        return password