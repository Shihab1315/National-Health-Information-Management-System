# doctors/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Doctor, Specialty
from .forms import DoctorForm
from accounts.decorators import role_required

@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_list(request):
    doctors = Doctor.objects.all()

    # Search
    search_query = request.GET.get('q')
    if search_query:
        doctors = doctors.filter(
            Q(full_name__icontains=search_query) |
            Q(doctor_id__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(specialties__name__icontains=search_query)
        ).distinct()

    # Filter by specialty
    specialty_filter = request.GET.get('specialty')
    if specialty_filter:
        doctors = doctors.filter(specialties__id=specialty_filter)

    # Filter by hospital
    hospital_filter = request.GET.get('hospital')
    if hospital_filter:
        doctors = doctors.filter(hospital__id=hospital_filter)

    # Filter by district
    district_filter = request.GET.get('district')
    if district_filter:
        doctors = doctors.filter(district=district_filter)

    # Pagination
    paginator = Paginator(doctors, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get distinct filters for dropdowns
    specialties = Specialty.objects.filter(is_active=True).order_by('name')
    districts = Doctor.objects.exclude(district__isnull=True).exclude(district='').values_list('district', flat=True).distinct().order_by('district')

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'specialty_filter': specialty_filter,
        'hospital_filter': hospital_filter,
        'district_filter': district_filter,
        'specialties': specialties,
        'districts': districts,
    }
    return render(request, 'doctors/doctor_list.html', context)


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    return render(request, 'doctors/doctor_detail.html', {'doctor': doctor})


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'Doctor {doctor.full_name} added successfully!')
            return redirect('doctors:detail', pk=doctor.pk)
    else:
        form = DoctorForm()
    
    # (ঐচ্ছিক) টেমপ্লেটে প্রয়োজনে সব স্পেশালিটি পাস করা
    specialties = Specialty.objects.filter(is_active=True).order_by('name')
    context = {
        'form': form,
        'title': 'Add New Doctor',
        'specialties': specialties,  # টেমপ্লেটে ব্যবহার করতে পারেন
    }
    return render(request, 'doctors/doctor_form.html', context)


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_update(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Doctor {doctor.full_name} updated successfully!')
            return redirect('doctors:detail', pk=doctor.pk)
    else:
        form = DoctorForm(instance=doctor)
    
    specialties = Specialty.objects.filter(is_active=True).order_by('name')
    context = {
        'form': form,
        'title': 'Edit Doctor',
        'doctor': doctor,
        'specialties': specialties,
    }
    return render(request, 'doctors/doctor_form.html', context)


@login_required
@role_required(['super_admin','hospital_admin'])
def doctor_delete(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        doctor.delete()
        messages.success(request, 'Doctor deleted successfully.')
        return redirect('doctors:list')
    return render(request, 'doctors/doctor_confirm_delete.html', {'doctor': doctor})