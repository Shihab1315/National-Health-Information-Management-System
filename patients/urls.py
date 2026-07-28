from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.patient_list, name='list'),
    path('create/', views.patient_create, name='create'),
    path('<int:pk>/', views.patient_detail, name='detail'),
    path('<int:pk>/update/', views.patient_update, name='update'),
    path('<int:pk>/delete/', views.patient_delete, name='delete'),
    path('profile/', views.patient_profile, name='profile'),
    path('profile/edit/', views.edit_patient_profile, name='edit_profile'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('profile/emergency-contact/', views.emergency_contact, name='emergency_contact'),
    path('profile/medical-information/', views.medical_information, name='medical_information'),
    path('profile/insurance/', views.insurance_information, name='insurance_information'),
    path('profile/patient-card/', views.download_patient_card, name='patient_card'),
    path('profile/patient-card/print/', views.print_patient_card, name='patient_card_print'),
    path('profile/completion/', views.profile_completion_dashboard, name='profile_completion'),
]