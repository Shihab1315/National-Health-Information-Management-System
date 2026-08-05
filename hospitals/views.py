from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from accounts.decorators import role_required
from django.utils import timezone

from appointments.models import Appointment
from doctors.models import Doctor
from .models import Hospital, HospitalDepartment, HospitalFacility, HospitalGallery, HospitalReview, HospitalOperatingHour
from .forms import HospitalForm
from .services import get_dashboard_stats, hospital_search_filter
 
import json


@login_required
@role_required(['super_admin'])
def dashboard(request):
    stats = get_dashboard_stats()
    latest = Hospital.objects.filter(is_deleted=False).order_by('-created_at')[:5]
    top_rated = Hospital.objects.filter(is_deleted=False, average_rating__gt=0).order_by('-average_rating')[:5]
    featured = Hospital.objects.filter(is_deleted=False, featured=True)[:4]
    context = {
        'stats': stats,
        'latest': latest,
        'top_rated': top_rated,
        'featured': featured,
    }
    return render(request, 'hospitals/dashboard.html', context)

@login_required
@role_required(['super_admin'])

def hospital_list(request):
    hospitals = Hospital.objects.filter(is_deleted=False)

    # Search & filter via service
    q = request.GET.get('q')
    district = request.GET.get('district')
    division = request.GET.get('division')
    hospital_type = request.GET.get('type')
    verified = request.GET.get('verified')
    emergency = request.GET.get('emergency')
    min_rating = request.GET.get('min_rating')

    if q:
        hospitals = hospitals.filter(
            Q(name__icontains=q) |
            Q(hospital_code__icontains=q) |
            Q(registration_number__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q)
        )
    if district:
        hospitals = hospitals.filter(district=district)
    if division:
        hospitals = hospitals.filter(division=division)
    if hospital_type:
        hospitals = hospitals.filter(hospital_type=hospital_type)
    if verified == 'true':
        hospitals = hospitals.filter(verified=True)
    if emergency == 'true':
        hospitals = hospitals.filter(emergency_available=True)
    if min_rating:
        hospitals = hospitals.filter(average_rating__gte=float(min_rating))

    # Pagination
    paginator = Paginator(hospitals, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # For filter dropdowns
    districts = Hospital.objects.filter(is_deleted=False).values_list('district', flat=True).distinct().order_by('district')
    divisions = Hospital.objects.filter(is_deleted=False).values_list('division', flat=True).distinct().order_by('division')

    context = {
        'page_obj': page_obj,
        'search_query': q,
        'district_filter': district,
        'division_filter': division,
        'type_filter': hospital_type,
        'verified_filter': verified,
        'emergency_filter': emergency,
        'min_rating_filter': min_rating,
        'districts': districts,
        'divisions': divisions,
        'hospital_types': Hospital._meta.get_field('hospital_type').choices,
    }
    return render(request, 'hospitals/hospital_list.html', context)

@login_required
@role_required(['super_admin'])
def hospital_detail(request, slug):
    hospital = get_object_or_404(Hospital, slug=slug, is_deleted=False)
    departments = HospitalDepartment.objects.filter(hospital=hospital, active=True)
    facilities = HospitalFacility.objects.filter(hospital=hospital, available=True).order_by('display_order')
    gallery = HospitalGallery.objects.filter(hospital=hospital).order_by('display_order')
    reviews = HospitalReview.objects.filter(hospital=hospital, approved=True).order_by('-created_at')
    operating_hours = HospitalOperatingHour.objects.filter(hospital=hospital).order_by('day')
    context = {
        'hospital': hospital,
        'departments': departments,
        'facilities': facilities,
        'gallery': gallery,
        'reviews': reviews,
        'operating_hours': operating_hours,
    }
    return render(request, 'hospitals/hospital_detail.html', context)

@login_required
@role_required(['super_admin'])
def hospital_create(request):
    if request.method == 'POST':
        form = HospitalForm(request.POST, request.FILES)
        if form.is_valid():
            hospital = form.save(commit=False)
            hospital.created_by = request.user
            hospital.save()
            messages.success(request, f'Hospital "{hospital.name}" created successfully!')
            return redirect('hospitals:detail', slug=hospital.slug)
    else:
        form = HospitalForm()
    return render(request, 'hospitals/hospital_create.html', {'form': form})

@login_required
@role_required(['super_admin'])
def hospital_update(request, slug):
    hospital = get_object_or_404(Hospital, slug=slug, is_deleted=False)
    if request.method == 'POST':
        form = HospitalForm(request.POST, request.FILES, instance=hospital)
        if form.is_valid():
            form.save()
            messages.success(request, f'Hospital "{hospital.name}" updated successfully!')
            return redirect('hospitals:detail', slug=hospital.slug)
    else:
        form = HospitalForm(instance=hospital)
    return render(request, 'hospitals/hospital_create.html', {'form': form, 'update': True, 'hospital': hospital})

@login_required
@role_required(['super_admin'])
def hospital_delete(request, slug):
    hospital = get_object_or_404(Hospital, slug=slug, is_deleted=False)
    if request.method == 'POST':
        hospital.is_deleted = True
        hospital.save()
        messages.success(request, 'Hospital deleted successfully.')
        return redirect('hospitals:list')
    return render(request, 'hospitals/hospital_confirm_delete.html', {'hospital': hospital})

@login_required
@role_required(['super_admin'])
def hospital_gallery(request, slug):
    hospital = get_object_or_404(Hospital, slug=slug, is_deleted=False)
    return render(request, 'hospitals/hospital_gallery.html', {'hospital': hospital})

@login_required
@role_required(['super_admin'])
def hospital_statistics(request, slug):
    hospital = get_object_or_404(Hospital, slug=slug, is_deleted=False)
    # Additional stats could be computed
    return render(request, 'hospitals/hospital_statistics.html', {'hospital': hospital})



