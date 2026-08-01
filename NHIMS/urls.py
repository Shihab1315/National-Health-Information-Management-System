from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

# def home(request):
#     return render(request, "dashboard/homepage.html")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("dashboard.urls")),
    path('patients/', include('patients.urls')),
    path('doctors/', include('doctors.urls')),
    path('appointments/', include('appointments.urls')),
    path('prescriptions/', include('prescriptions.urls')),
     path('hospitals/', include('hospitals.urls')),
     path('laboratory/', include('laboratory.urls')),
      path('pharmacy/', include('pharmacy.urls')),
      path('medical-records/', include('medical_records.urls')),
      path('analytics/', include('analytics.urls')),
      path('notifications/', include('notifications.urls')),
      path('superadmin/', include('superadmin.urls')),
      path('hospital-admin/',include('hospital_admin.urls')),




]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)