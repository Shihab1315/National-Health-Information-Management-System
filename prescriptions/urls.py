# prescriptions/urls.py
"""
URL configuration for the Prescription module.

Defines all routes for prescription management, including dashboard,
list, create, detail, update, delete (soft), issue, complete, cancel,
print, and AJAX endpoints.
"""

from django.urls import path

from . import views

app_name = 'prescriptions'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.PrescriptionDashboardView.as_view(), name='dashboard'),

    # List view (with search, filter, pagination)
    path('', views.PrescriptionListView.as_view(), name='list'),
    
    
    path('my-prescriptions/', views.patient_my_prescriptions, name='patient_my_prescriptions'),
    path('my-prescriptions/<int:pk>/', views.patient_prescription_detail, name='patient_prescription_detail'),
    path('my-prescriptions/<int:pk>/download/', views.patient_prescription_download, name='patient_prescription_download'),
    path('my-prescriptions/<int:pk>/print/', views.patient_prescription_print, name='patient_prescription_print'),
    # CRUD
    path('create/', views.PrescriptionCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PrescriptionDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PrescriptionUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.PrescriptionDeleteView.as_view(), name='delete'),

    # Quick actions (POST only)
    path('<int:pk>/issue/', views.PrescriptionIssueView.as_view(), name='issue'),
    path('<int:pk>/complete/', views.PrescriptionCompleteView.as_view(), name='complete'),
    path('<int:pk>/cancel/', views.PrescriptionCancelView.as_view(), name='cancel'),

    # Print (GET)
    path('<int:pk>/print/', views.PrescriptionPrintView.as_view(), name='print'),

    # AJAX endpoints
    path('api/appointment-data/', views.AppointmentDataView.as_view(), name='appointment_data'),
]