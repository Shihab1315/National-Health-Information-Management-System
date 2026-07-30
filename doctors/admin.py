# doctors/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Specialty, Doctor, DoctorAvailability


# ============================================================================
# Specialty Admin
# ============================================================================
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)


# ============================================================================
# Doctor Inline for User Admin
# ============================================================================
class DoctorInline(admin.StackedInline):
    """Inline Doctor profile in User admin."""
    model = Doctor
    can_delete = False
    verbose_name_plural = 'Doctor Profile'
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'full_name', 'national_id', 'registration_number',
                'gender', 'date_of_birth'
            )
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'address', 'city', 'district', 'zip_code')
        }),
        ('Professional', {
            'fields': ('specialties', 'hospital', 'qualification', 
                      'experience', 'consultation_fee')
        }),
        ('Schedule', {
            'fields': ('available_days', 'available_time_start', 'available_time_end')
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'profile_photo', 'bio')
        }),
    )
    extra = 0


# ============================================================================
# Custom User Admin with Doctor Inline
# ============================================================================
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Enhanced User admin with Doctor inline."""
    inlines = [DoctorInline]
    
    list_display = ('username', 'email', 'first_name', 'last_name', 
                   'is_staff', 'is_active', 'doctor_status')
    list_filter = ('is_staff', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 
                                   'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    def doctor_status(self, obj):
        """Display doctor profile status."""
        try:
            doctor = Doctor.objects.get(user=obj)
            if doctor.is_verified:
                return format_html(
                    '<span style="color: green; font-weight: bold;">✅ Verified Doctor</span>'
                )
            return format_html(
                    '<span style="color: orange; font-weight: bold;">⏳ Unverified Doctor</span>'
                )
        except Doctor.DoesNotExist:
            return format_html(
                '<span style="color: gray;">Not a doctor</span>'
            )
    doctor_status.short_description = 'Doctor Status'


# ============================================================================
# Doctor Creation Form
# ============================================================================
class DoctorCreationForm(forms.ModelForm):
    """Form for creating Doctor with User account."""
    
    username = forms.CharField(
        max_length=150, 
        required=False,
        help_text='Required for new doctors. Leave blank if linking to existing user.'
    )
    password = forms.CharField(
        widget=forms.PasswordInput, 
        required=False,
        help_text='Enter a strong password for new user.'
    )
    email = forms.EmailField(
        required=False,
        help_text='Will be synced with User account.'
    )
    create_user = forms.BooleanField(
        required=False,
        initial=True,
        help_text='Create a new User account for this doctor.'
    )
    
    class Meta:
        model = Doctor
        exclude = ['user', 'doctor_id', 'created_at', 'updated_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and instance.user:
            # Editing existing doctor with user
            self.fields['username'].initial = instance.user.username
            self.fields['username'].required = False
            self.fields['email'].initial = instance.user.email
            self.fields['create_user'].initial = False
            self.fields['create_user'].widget.attrs['disabled'] = True
    
    def clean(self):
        cleaned_data = super().clean()
        create_user = cleaned_data.get('create_user', True)
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        email = cleaned_data.get('email')
        
        if create_user:
            if not username:
                raise ValidationError('Username is required when creating a new user.')
            if not password:
                raise ValidationError('Password is required when creating a new user.')
            if User.objects.filter(username=username).exists():
                raise ValidationError(f'Username "{username}" already exists.')
            if email and User.objects.filter(email=email).exists():
                raise ValidationError(f'Email "{email}" already in use.')
        
        return cleaned_data


# ============================================================================
# Doctor Admin (Main)
# ============================================================================
@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """Enhanced Doctor admin with User management."""
    
    form = DoctorCreationForm
    list_display = (
        'full_name', 'doctor_id', 'registration_number', 
        'specialty_list', 'hospital', 'experience',
        'user_status', 'is_active', 'is_verified'
    )
    list_filter = ('is_active', 'is_verified', 'gender', 'specialties', 'hospital')
    search_fields = (
        'full_name', 'doctor_id', 'registration_number',
        'national_id', 'phone', 'user__username'
    )
    readonly_fields = ('doctor_id', 'created_at', 'updated_at')
    filter_horizontal = ('specialties',)
    
    fieldsets = (
        ('User Account', {
            'fields': ('create_user', 'username', 'password'),
            'description': (
                'IMPORTANT: Every doctor must have a linked User account. '
                'If User is null, the doctor will NOT appear in booking forms.'
            )
        }),
        ('Personal Information', {
            'fields': ('full_name', 'national_id', 'registration_number',
                       'gender', 'date_of_birth', 'phone')
        }),
        ('Contact & Address', {
            'fields': ('address', 'city', 'district', 'zip_code', 'email')
        }),
        ('Professional', {
            'fields': ('specialties', 'hospital', 'qualification',
                       'experience', 'consultation_fee')
        }),
        ('Schedule', {
            'fields': ('available_days', 'available_time_start', 'available_time_end')
        }),
        ('Profile', {
            'fields': ('profile_photo', 'bio', 'is_active', 'is_verified')
        }),
        ('System', {
            'fields': ('doctor_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_verified', 'make_unverified', 'fix_orphan_doctors']
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on whether creating or editing."""
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.user:
            # Editing existing doctor - make fields read-only
            form.base_fields['username'].widget.attrs['readonly'] = True
            form.base_fields['username'].required = False
        return form
    
    def save_model(self, request, obj, form, change):
        """Handle saving with User creation."""
        create_user = form.cleaned_data.get('create_user', True)
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        email = form.cleaned_data.get('email')
        
        if not change or not obj.user:
            # Creating new doctor
            if create_user and username and password:
                with transaction.atomic():
                    # Create User
                    user = User.objects.create_user(
                        username=username,
                        password=password,
                        email=email or ''
                    )
                    user.role = 'doctor'
                    user.save()
                    obj.user = user
        elif obj.user:
            # Update existing User
            if username:
                obj.user.username = username
            if email:
                obj.user.email = email
            if password:
                obj.user.set_password(password)
            obj.user.save()
        
        # Save the doctor
        obj.save()
    
    def specialty_list(self, obj):
        return ", ".join([s.name for s in obj.specialties.all()][:3])
    specialty_list.short_description = 'Specialties'
    
    def user_status(self, obj):
        """Show User account status."""
        if obj.user:
            if obj.user.is_active:
                return format_html(
                    '<span style="color: green; font-weight: bold;">✅ Active</span>'
                )
            return format_html(
                '<span style="color: red; font-weight: bold;">❌ Inactive</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold; background: #ffebee; padding: 2px 6px; border-radius: 4px;">⚠️ No User</span>'
        )
    user_status.short_description = 'User Status'
    
    def make_verified(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f'{queryset.count()} doctors verified.')
    make_verified.short_description = "✅ Verify selected doctors"
    
    def make_unverified(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, f'{queryset.count()} doctors unverified.')
    make_unverified.short_description = "❌ Unverify selected doctors"
    
    def fix_orphan_doctors(self, request, queryset):
        """Admin action to fix doctors without User accounts."""
        from django.contrib.auth.models import User
        from django.db import transaction
        
        fixed_count = 0
        failed_count = 0
        
        for doctor in queryset.filter(user__isnull=True):
            try:
                with transaction.atomic():
                    # Generate username from registration number or full_name
                    base_username = f"dr_{doctor.registration_number.lower()}"
                    base_username = ''.join(c for c in base_username if c.isalnum() or c == '_')
                    
                    # Ensure uniqueness
                    counter = 1
                    username = base_username[:150]
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username[:140]}_{counter}"[:150]
                        counter += 1
                    
                    email = doctor.email or f"{username}@nhims.local"
                    
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=User.objects.make_random_password(length=12)
                    )
                    user.role = 'doctor'
                    
                    # Set name from doctor
                    if doctor.full_name and doctor.full_name != 'Unknown':
                        name_parts = doctor.full_name.split(maxsplit=1)
                        user.first_name = name_parts[0] if name_parts else ''
                        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    user.save()
                    
                    doctor.user = user
                    doctor.save()
                    fixed_count += 1
                    
            except Exception as e:
                failed_count += 1
                self.message_user(request, f'Failed to fix doctor {doctor.id}: {e}', level='ERROR')
        
        if fixed_count > 0:
            self.message_user(request, f'✅ Fixed {fixed_count} doctors.')
        if failed_count > 0:
            self.message_user(request, f'❌ Failed to fix {failed_count} doctors.', level='ERROR')
    
    fix_orphan_doctors.short_description = '🔧 Fix doctors without User accounts'


# ============================================================================
# Doctor Availability Admin
# ============================================================================
@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'get_day_display', 'start_time', 'end_time', 'is_available')
    list_filter = ('doctor', 'day_of_week', 'is_available')
    search_fields = ('doctor__full_name', 'doctor__registration_number')
    
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Day'