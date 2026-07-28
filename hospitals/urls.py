from django.urls import path
from . import views

app_name = 'hospitals'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('list/', views.hospital_list, name='list'),
    path('create/', views.hospital_create, name='create'),
    path('<slug:slug>/', views.hospital_detail, name='detail'),
    path('<slug:slug>/update/', views.hospital_update, name='update'),
    path('<slug:slug>/delete/', views.hospital_delete, name='delete'),
    path('<slug:slug>/gallery/', views.hospital_gallery, name='gallery'),
    path('<slug:slug>/statistics/', views.hospital_statistics, name='statistics'),
]