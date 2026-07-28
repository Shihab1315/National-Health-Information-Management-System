from django.urls import path
from .views import homepage, admin_dashboard, doctor_dashboard,patient_dashboard

app_name = 'dashboard'

urlpatterns = [
    path('', homepage, name='homepage'),
    path('admin_d/', admin_dashboard, name='admin_dashboard'),
    path('doctor_d/', doctor_dashboard, name='doctor_dashboard'),
    path('patient_d/', patient_dashboard, name='patient_dashboard'),

]