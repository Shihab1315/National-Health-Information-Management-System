# hospital_admin/urls.py
from django.urls import path
from . import views

app_name = 'hospital_admin'

urlpatterns = [
    # Dashboard
    path('', views.HospitalAdminDashboardView.as_view(), name='dashboard'),
    
    # Verification
    path('verification/', views.HospitalVerificationView.as_view(), name='verification'),
    
    # Verification Wizard Steps
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
    
    # ===== Doctor Management =====
    path('doctors/dashboard/', views.DoctorDashboardView.as_view(), name='doctor_dashboard'),
    path('doctors/', views.AllDoctorsView.as_view(), name='doctor_list'),
    path('doctors/add/', views.AddDoctorRequestView.as_view(), name='add_doctor'),
    
    # ===== Doctor Verification =====
    path('doctors/verification/', views.DoctorVerificationView.as_view(), name='doctor_verification'),
    path('doctors/verification/<int:doctor_id>/', views.DoctorVerificationDetailView.as_view(), name='doctor_verification_detail'),
   path('doctors/verification/<int:doctor_id>/approve/', views.approve_doctor, name='approve_doctor'),
    path('doctors/verification/<int:doctor_id>/reject/', views.reject_doctor, name='reject_doctor'),
    path('doctors/verification/<int:doctor_id>/detail/', 
     views.PendingDoctorDetailView.as_view(), 
     name='pending_doctor_detail'),
    # ===== Departments =====
    path('departments/', views.DepartmentListView.as_view(), name='departments'),
    path('departments/', views.AllDepartmentsView.as_view(), name='all_departments'),
    path('departments/add/', views.AddDepartmentView.as_view(), name='add_department'),
     path('departments/<int:department_id>/edit/', views.EditDepartmentView.as_view(), name='edit_department'),
    path('departments/<int:department_id>/', views.DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<int:department_id>/toggle/', views.toggle_department_status, name='toggle_department'),
    path('departments/<int:department_id>/delete/', views.delete_department, name='delete_department'),
    path('departments/dashboard/', views.DepartmentDashboardView.as_view(), name='department_dashboard'),
    path('doctors/verification/<int:doctor_id>/deactivate/', views.deactivate_doctor, name='deactivate_doctor'),
    
     
    # ===== Department Heads =====
    path('departments/heads/', views.DepartmentHeadsView.as_view(), name='department_heads'),
    path('departments/heads/assign/', views.assign_department_head, name='assign_department_head'),
    path('departments/heads/<int:department_id>/change/', views.change_department_head, name='change_department_head'),
    path('departments/heads/<int:department_id>/remove/', views.remove_department_head, name='remove_department_head'),
    path('departments/heads/doctors/', views.get_available_doctors, name='get_available_doctors'),
    # ===== Rooms & Units =====
    path('rooms/', views.RoomsAndUnitsView.as_view(), name='rooms'),
    path('rooms/add/', views.add_room, name='add_room'),
    path('rooms/<int:room_id>/edit/', views.edit_room, name='edit_room'),
    path('rooms/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('rooms/<int:room_id>/detail/', views.room_detail, name='room_detail'),
    path('rooms/<int:room_id>/toggle-status/', views.toggle_room_status, name='toggle_room_status'),
    # ===== Appointment Management =====
     path('appointments/dashboard/', views.AppointmentDashboardView.as_view(), name='appointment_dashboard'),
    path('appointments/', views.AppointmentListView.as_view(), name='appointments'),
    path('appointments/<int:appointment_id>/', views.AppointmentDetailView.as_view(), name='appointment_detail'),
    path('appointments/<int:appointment_id>/approve/', views.approve_appointment, name='approve_appointment'),
    path('appointments/<int:appointment_id>/reject/', views.reject_appointment, name='reject_appointment'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/calendar/', views.AppointmentCalendarView.as_view(), name='appointment_calendar'),  
    # Locked modules
    path('appointments/', views.LockedModuleView.as_view(), name='appointments'),
    path('settings/', views.LockedModuleView.as_view(), name='settings'),
]