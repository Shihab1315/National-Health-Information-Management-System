"""
URL configuration for the Appointment module.
"""

from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # ---------- Dashboard (staff/admin) ----------
    path('dashboard/', views.AppointmentDashboardView.as_view(), name='dashboard'),

    # ---------- Main list (staff/admin) ----------
    path('', views.AppointmentListView.as_view(), name='list'),

    # ---------- Filtered lists (staff/admin) ----------
    path('today/', views.TodayAppointmentsView.as_view(), name='today'),
    path('upcoming/', views.UpcomingAppointmentsView.as_view(), name='upcoming'),
    path('completed/', views.CompletedAppointmentsView.as_view(), name='completed'),
    path('cancelled/', views.CancelledAppointmentsView.as_view(), name='cancelled'),

    # ---------- Patient‑specific URLs ----------
    # List of patient's own appointments
    path('my-appointments/', views.patient_appointment_list, name='patient_appointment_list'),
    # Detail of a single appointment (patient only)
    path('my-appointments/<int:pk>/', views.patient_appointment_detail, name='patient_appointment_detail'),
    # Booking wizard (patient only)
    path('book/', views.patient_book_appointment, name='patient_book_appointment'),
    path('my-appointments/<int:pk>/cancel/', views.patient_cancel_appointment, name='patient_cancel_appointment'),
    path('my-appointments/<int:pk>/reschedule/', views.patient_reschedule_appointment, name='patient_reschedule_appointment'),
    path('my-appointments/history/', views.patient_appointment_history, name='patient_appointment_history'),
    path('my-appointments/<int:pk>/slip/', views.patient_appointment_slip_preview, name='patient_appointment_slip_preview'),
    path('my-appointments/<int:pk>/slip/download/', views.patient_appointment_slip_pdf, name='patient_appointment_slip_pdf'),
    path('my-appointments/<int:pk>/slip/print/', views.patient_appointment_slip_print, name='patient_appointment_slip_print'),
    # ---------- CRUD (staff/admin) ----------
    path('create/', views.AppointmentCreateView.as_view(), name='create'),
    path('<int:pk>/', views.AppointmentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.AppointmentUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.AppointmentDeleteView.as_view(), name='delete'),

    # ---------- Quick actions (POST) ----------
    path('<int:pk>/confirm/', views.AppointmentConfirmView.as_view(), name='confirm'),
    path('<int:pk>/cancel/', views.AppointmentCancelView.as_view(), name='cancel'),
    path('<int:pk>/complete/', views.AppointmentCompleteView.as_view(), name='complete'),

    # ---------- AJAX endpoints ----------
    # Existing (staff/admin)
    path('check-availability/', views.DoctorAvailabilityView.as_view(), name='check_availability'),
    path('api/doctors-by-hospital/', views.doctors_by_hospital, name='doctors_by_hospital'),

    # New (patient booking wizard)
    path('api/doctors/', views.get_doctors_ajax, name='get_doctors_ajax'),
    path('api/available-dates/', views.get_available_dates_ajax, name='get_available_dates_ajax'),
    path('api/available-slots/', views.get_available_slots_ajax, name='get_available_slots_ajax'),
]