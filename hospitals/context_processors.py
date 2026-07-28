from .services import get_dashboard_stats

def hospitals_stats(request):
    # For global use, e.g. in navbar or sidebar
    if request.user.is_authenticated:
        stats = get_dashboard_stats()
        return {'hospital_stats': stats}
    return {}