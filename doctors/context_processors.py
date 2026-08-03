from .models import Doctor

def doctor_verification_status(request):
    if request.user.is_authenticated:
        try:
            doctor = Doctor.objects.get(user=request.user)
            return {'is_verified': doctor.is_verified}
        except Doctor.DoesNotExist:
            pass
    return {'is_verified': False}