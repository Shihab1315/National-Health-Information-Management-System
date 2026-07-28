from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from .models import Hospital


def get_dashboard_stats():
    today = timezone.now().date()
    total = Hospital.objects.filter(is_deleted=False).count()
    government = Hospital.objects.filter(is_deleted=False, hospital_type='gov').count()
    private = Hospital.objects.filter(is_deleted=False, hospital_type='private').count()
    featured = Hospital.objects.filter(is_deleted=False, featured=True).count()
    verified = Hospital.objects.filter(is_deleted=False, verified=True).count()
    emergency = Hospital.objects.filter(is_deleted=False, emergency_available=True).count()
    added_today = Hospital.objects.filter(is_deleted=False, created_at__date=today).count()

    total_beds = Hospital.objects.filter(is_deleted=False).aggregate(Sum('total_beds'))['total_beds__sum'] or 0
    available_beds = Hospital.objects.filter(is_deleted=False).aggregate(Sum('available_beds'))['available_beds__sum'] or 0
    icu_beds = Hospital.objects.filter(is_deleted=False).aggregate(Sum('icu_beds'))['icu_beds__sum'] or 0
    avg_rating = Hospital.objects.filter(is_deleted=False, average_rating__gt=0).aggregate(Avg('average_rating'))['average_rating__avg'] or 0

    return {
        'total': total,
        'government': government,
        'private': private,
        'featured': featured,
        'verified': verified,
        'emergency': emergency,
        'added_today': added_today,
        'total_beds': total_beds,
        'available_beds': available_beds,
        'icu_beds': icu_beds,
        'avg_rating': round(avg_rating, 2),
    }


def hospital_search_filter(queryset, search_params):
    # Similar logic as in view – can be used in API or advanced search
    pass