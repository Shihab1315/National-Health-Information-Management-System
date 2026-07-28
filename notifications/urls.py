from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationCenterView.as_view(), name='center'),
    path('mark-read/<int:pk>/', views.mark_as_read_ajax, name='mark_read'),
    path('mark-all-read/', views.mark_all_as_read_ajax, name='mark_all_read'),
    path('delete/<int:pk>/', views.delete_notification_ajax, name='delete'),
    path('delete-all-read/', views.delete_all_read_ajax, name='delete_all_read'),
    path('unread-count/', views.unread_count, name='unread_count'),  # ✅ added
]