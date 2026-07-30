# laboratory/urls.py
"""
URL configuration for the Laboratory module.

Defines all routes for managing lab orders, tests, categories, and results.
All URLs are namespaced under 'laboratory'.
"""

from django.urls import path
from . import views

app_name = 'laboratory'

urlpatterns = [
    # ----- Lab Orders -----
    path('', views.LabOrderListView.as_view(), name='order_list'),
    path('create/', views.LabOrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.LabOrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/edit/', views.LabOrderUpdateView.as_view(), name='order_update'),
    path('<int:pk>/delete/', views.LabOrderDeleteView.as_view(), name='order_delete'),
    path(
    'dashboard/',
    views.LaboratoryDashboardView.as_view(),
    name='dashboard'
),
    # ----- Lab Result Upload (for a specific order item) -----
    path('<int:order_pk>/item/<int:item_pk>/result/', views.LabResultUploadView.as_view(), name='upload_result'),

    # ----- Laboratory Tests (catalogue) -----
    path('tests/', views.LaboratoryTestListView.as_view(), name='test_list'),
    path('tests/create/', views.LaboratoryTestCreateView.as_view(), name='test_create'),
    path('tests/<int:pk>/edit/', views.LaboratoryTestUpdateView.as_view(), name='test_update'),
    path('tests/<int:pk>/delete/', views.LaboratoryTestDeleteView.as_view(), name='test_delete'),


    path('my-reports/', views.patient_lab_report_list, name='patient_lab_report_list'),
    path('my-reports/<int:pk>/', views.patient_lab_report_detail, name='patient_lab_report_detail'),
    path('my-reports/<int:pk>/download/', views.patient_download_lab_report_pdf, name='patient_download_lab_report_pdf'),
    path('my-reports/<int:pk>/print/', views.patient_print_lab_report, name='patient_print_lab_report'),
    path('history/', views.patient_lab_history, name='patient_lab_history'),


    # ----- Test Categories -----
    path('categories/', views.TestCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.TestCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.TestCategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.TestCategoryDeleteView.as_view(), name='category_delete'),
     # Doctor - My Lab Requests
     path('my-lab-requests/', views.DoctorLabRequestListView.as_view(), name='doctor_lab_requests'),
     path('doctor/requests/<int:pk>/', views.DoctorLabRequestDetailView.as_view(), name='doctor_lab_request_detail'),
     path('doctor/create/', views.DoctorLabRequestCreateView.as_view(), name='doctor_lab_request_create'),
     path('doctor/<int:pk>/edit/', views.DoctorLabRequestUpdateView.as_view(), name='doctor_lab_request_edit'),
    path('doctor/<int:pk>/cancel/', views.DoctorLabRequestCancelView.as_view(), name='doctor_lab_request_cancel'),
    path('doctor/<int:pk>/progress/', views.DoctorLabProgressView.as_view(), name='doctor_lab_progress'),
]