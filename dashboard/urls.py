
from django import views
from django.urls import path
from .views import homepage, homepage_doctors, homepage_hospitals, lab_technician_dashboard, superadmin_dashboard, doctor_dashboard, patient_dashboard,home_hospital_details
from hospitals.views import hospital_detail

app_name = 'dashboard'

urlpatterns = [
    path('', homepage, name='homepage'),
    path('superadmin_d/', superadmin_dashboard, name='superadmin_dashboard'),
    path('doctor_d/', doctor_dashboard, name='doctor_dashboard'),
    path('patient_d/', patient_dashboard, name='patient_dashboard'),
    #  path('lab_technician_d/', lab_technician_dashboard, name='lab_technician_dashboard'),
   
     # ===== HOMEPAGE DOCTORS PAGE =====
    path('doctors/', homepage_doctors, name='homepage_doctors'),
     # ===== HOMEPAGE HOSPITALS =====
    path('hospitals/', homepage_hospitals, name='homepage_hospitals'),
    path('hospitals/<int:pk>/', hospital_detail, name='hospital_detail'),
     # ===== HOME HOSPITAL DETAIL =====
     path('hospital-detail/<int:pk>/', home_hospital_details, name='home_hospital_details'),

]