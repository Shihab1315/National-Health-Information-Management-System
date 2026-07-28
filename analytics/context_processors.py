from .services import get_dashboard_stats

def analytics_stats(request):
    """
    Context processor to inject dashboard statistics into every template.
    This makes the stats available globally without needing to pass them in every view.
    Usage: {{ analytics_stats.total_patients }} in any template.
    """
    if request.user.is_authenticated:
        return {'analytics_stats': get_dashboard_stats()}
    return {}