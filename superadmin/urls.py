# superadmin/urls.py
from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    # Dashboard
    path('', views.superadmin_dashboard, name='dashboard'),
    path('dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    
    # Hospital Management
    path('hospitals/all/', views.AllHospitalListView.as_view(), name='all_hospitals'),
    path('hospitals/pending/', views.PendingHospitalApplicationListView.as_view(), name='pending_hospital_applications'),
    path('hospitals/approved/', views.ApprovedHospitalListView.as_view(), name='approved_hospitals'),
    path('hospitals/rejected/', views.RejectedHospitalListView.as_view(), name='rejected_hospitals'),
    path('hospitals/<int:hospital_id>/', views.HospitalDetailView.as_view(), name='hospital_detail'),
    path('hospitals/<int:hospital_id>/status/', views.update_hospital_status, name='update_hospital_status'),
    
    # ===== Hospital Application Detail - Using UUID =====
    path('hospital-management/application/<uuid:application_id>/', 
         views.HospitalApplicationDetailView.as_view(), 
         name='hospital_application_detail'),
    
    # ===== Application Actions - Using UUID =====
    path('application/<uuid:application_id>/approve/', 
         views.approve_application, 
         name='approve_application'),
    path('application/<uuid:application_id>/reject/', 
         views.reject_application, 
         name='reject_application'),
    path('application/<uuid:application_id>/more-info/', 
         views.request_more_info, 
         name='request_more_info'),
        # ===== NEW: User Management =====
    path('users/', views.AllUsersView.as_view(), name='all_users'),
    path('users/<int:user_id>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('settings/profile/', views.SuperAdminProfileView.as_view(), name='profile'),
    path('settings/change-password/', views.SuperAdminChangePasswordView.as_view(), name='change_password'),
    # API
    path('api/pending-count/', views.pending_hospital_applications_count, name='pending_count'),
    
]