from django.urls import path
from . import views

app_name = 'analytics'


def global_search_view(request):
    query = request.GET.get('query', '')
    return views.global_search(query)


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path(
        'global-search/',
        global_search_view,
        name='global_search'
    ),
    path("reports/", views.reports, name="reports"),
    path("settings/", views.settings, name="settings"), 
]