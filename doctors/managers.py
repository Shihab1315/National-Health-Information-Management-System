# doctors/managers.py
from django.db import models
from django.db.models import Q

class DoctorQuerySet(models.QuerySet):
    """Custom QuerySet for Doctor model."""
    
    def active(self):
        """Filter for doctors with active User accounts."""
        return self.filter(user__isnull=False, user__is_active=True)
    
    def with_user(self):
        """Prefetch User data."""
        return self.select_related('user')
    
    def available_for_booking(self):
        """Doctors available for patient booking."""
        return self.active().filter(
            is_available=True,
            is_verified=True
        )
    
    def in_hospital(self, hospital_id):
        """Doctors in a specific hospital."""
        return self.filter(hospital_id=hospital_id)


class DoctorManager(models.Manager):
    """Custom manager for Doctor model."""
    
    def get_queryset(self):
        return DoctorQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def available_for_booking(self):
        return self.get_queryset().available_for_booking()
    
    def get_by_user(self, user):
        """Get Doctor profile by User."""
        try:
            return self.get_queryset().get(user=user)
        except self.model.DoesNotExist:
            return None
    
    def create_doctor_with_user(self, user_data, doctor_data):
        """Create User and Doctor profile atomically."""
        from django.contrib.auth.models import User
        from django.db import transaction
        
        with transaction.atomic():
            # Create User
            user = User.objects.create_user(**user_data)
            # Assigning a role attribute to User may not be defined on the default
            # Django User model. Silence type checkers if a custom field exists.
            user.role = 'doctor'  # type: ignore[attr-defined]
            user.save()
            
            # Create Doctor profile
            doctor = self.model(
                user=user,
                **doctor_data
            )
            doctor.full_clean()
            doctor.save()
            
            return doctor