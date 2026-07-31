from django.urls import path
from .views import homepage, superadmin_dashboard, doctor_dashboard,patient_dashboard

app_name = 'dashboard'

urlpatterns = [
    path('', homepage, name='homepage'),
    path('superadmin_d/', superadmin_dashboard, name='superadmin_dashboard'),
    path('doctor_d/', doctor_dashboard, name='doctor_dashboard'),
    path('patient_d/', patient_dashboard, name='patient_dashboard'),

]