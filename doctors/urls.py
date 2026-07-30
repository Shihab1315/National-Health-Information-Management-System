from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('', views.doctor_list, name='list'),
    path('create/', views.doctor_create, name='create'),
    path('<int:pk>/', views.doctor_detail, name='detail'),
    path('<int:pk>/update/', views.doctor_update, name='update'),
    path('<int:pk>/delete/', views.doctor_delete, name='delete'),
    # Doctor Profile
    path('profile/', views.DoctorProfileView.as_view(), name='doctor_profile'),
     path('profile/edit/', views.DoctorProfileUpdateView.as_view(), name='doctor_profile_edit'),
    path('profile/photo/', views.DoctorProfilePhotoUpdateView.as_view(), name='doctor_change_photo'),
    path('profile/photo/remove/', views.DoctorProfilePhotoRemoveView.as_view(), name='doctor_remove_photo'),
     path('profile/change-password/', views.DoctorChangePasswordView.as_view(), name='doctor_change_password'),
      # Doctor Settings
    path('settings/', views.DoctorGeneralSettingsView.as_view(), name='doctor_general_settings'),
     path('settings/notifications/', views.DoctorNotificationSettingsView.as_view(), name='doctor_notification_settings'),
]