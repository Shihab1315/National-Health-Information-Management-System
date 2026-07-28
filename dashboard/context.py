from .services import DashboardService

def dashboard_context(request):
    # This will inject all dashboard data into every template
    return DashboardService.get_all_active_data()