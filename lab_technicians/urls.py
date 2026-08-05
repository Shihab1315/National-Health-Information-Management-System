# lab_technicians/urls.py
from django.urls import path
from . import views

app_name = 'lab_technicians'

urlpatterns = [
    path('', views.LabTechnicianListView.as_view(), name='list'),
    path('create/', views.LabTechnicianCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.LabTechnicianEditView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.LabTechnicianDeleteView.as_view(), name='delete'),
    
    # ===== LAB TECHNICIAN DASHBOARD (NEW) =====
    path('dashboard/', views.LabTechDashboardView.as_view(), name='dashboard'),
    
    # Test Orders
    path('test-orders/', views.TestOrderListView.as_view(), name='test_orders'),
    path('test-orders/<int:pk>/', views.TestOrderDetailView.as_view(), name='test_order_detail'),
    
    # Sample Collection
    path('test-orders/<int:pk>/collect/', views.collect_sample, name='collect_sample'),
    
    # Processing
    path('test-orders/<int:pk>/process/', views.start_processing, name='start_processing'),
    
    # Lab Results
    path('lab-results/<int:order_id>/', views.LabResultCreateView.as_view(), name='lab_result_create'),
    
    # Completed Reports
    path('completed-reports/', views.CompletedReportListView.as_view(), name='completed_reports'),
    path('completed-reports/<int:pk>/download/', views.download_report, name='download_report'),
    
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    
    # Settings
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('settings/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
]