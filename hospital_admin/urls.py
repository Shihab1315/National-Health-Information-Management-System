# hospital_admin/urls.py
from django.urls import path
from . import views

app_name = 'hospital_admin'

urlpatterns = [
    # Dashboard
    path('', views.HospitalAdminDashboardView.as_view(), name='dashboard'),
    
    # Verification
    path('verification/', views.HospitalVerificationView.as_view(), name='verification'),
    
    # ===== Verification Wizard Steps =====
    path('verification/hospital-information/', 
         views.HospitalInformationView.as_view(), 
         name='hospital_information'),
     path('verification/contact-information/', 
         views.HospitalVerificationContactView.as_view(), 
         name='verification_contact_information'),
     path('verification/address-information/', 
         views.HospitalVerificationAddressView.as_view(), 
         name='verification_address_information'),
     path('verification/documents/', 
         views.HospitalVerificationDocumentsView.as_view(), 
         name='verification_documents'),
      path('verification/review/', 
         views.HospitalVerificationReviewView.as_view(), 
         name='verification_review'),
    # Locked modules (placeholder)
    path('doctors/', views.LockedModuleView.as_view(), name='doctors'),
    path('departments/', views.LockedModuleView.as_view(), name='departments'),
    path('appointments/', views.LockedModuleView.as_view(), name='appointments'),
    path('settings/', views.LockedModuleView.as_view(), name='settings'),
]