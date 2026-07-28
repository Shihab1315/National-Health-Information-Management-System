# medical_records/urls.py

from django.urls import path

from . import views

app_name = "medical_records"

urlpatterns = [

    # ==========================================================
    # Dashboard
    # ==========================================================
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    # ==========================================================
    # Medical Records
    # ==========================================================
    path(
        "records/",
        views.RecordListView.as_view(),
        name="record_list",
    ),
    path(
        "records/create/",
        views.RecordCreateView.as_view(),
        name="record_create",
    ),
    path(
        "records/<int:pk>/",
        views.RecordDetailView.as_view(),
        name="record_detail",
    ),
    path(
        "records/<int:pk>/edit/",
        views.RecordUpdateView.as_view(),
        name="record_edit",
    ),
    path(
        "records/<int:pk>/delete/",
        views.RecordDeleteView.as_view(),
        name="record_delete",
    ),

    # ==========================================================
    # Patient Timeline
    # ==========================================================
    path(
        "timeline/<int:patient_id>/",
        views.patient_timeline,
        name="patient_timeline",
    ),

    # ==========================================================
    # Attachments
    # ==========================================================
    path(
        "attachments/upload/<int:record_id>/",
        views.attachment_upload,
        name="attachment_upload",
    ),
    path(
        "attachments/<int:pk>/",
        views.attachment_list,
        name="attachment_list",
    ),
    path('my-records/', views.patient_medical_record_list, name='patient_medical_record_list'),
    path('my-records/<int:pk>/', views.patient_medical_record_detail, name='patient_medical_record_detail'),
    path('my-records/<int:pk>/download/', views.download_medical_record_pdf, name='download_medical_record_pdf'),
    path('my-records/<int:pk>/print/', views.print_medical_record, name='print_medical_record'),
]