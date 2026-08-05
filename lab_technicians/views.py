# lab_technicians/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q

from accounts.decorators import role_required
from .models import LabTechnician
from .forms import CreateLabTechnicianForm, EditLabTechnicianForm
from hospitals.models import Hospital, HospitalApplication
from hospital_admin.models import HospitalAdminProfile
from accounts.decorators import role_required
from .models import LabTechnician
from .forms import CreateLabTechnicianForm, EditLabTechnicianForm
from hospitals.models import Hospital, HospitalApplication
from hospital_admin.models import HospitalAdminProfile
from laboratory.models import LabOrder, LabOrderItem, LabResult, LaboratoryTest
from patients.models import Patient
from doctors.models import Doctor
from django.contrib.auth import get_user_model, update_session_auth_hash

User = get_user_model()



@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class LabTechnicianListView(View):
    template_name = 'hospital_admin/lab_technicians/list.html'

    def get(self, request):
        print("=" * 60)
        print("🔍 LabTechnicianListView CALLED")
        print(f"User: {request.user.username}")
        print(f"Role: {request.user.role}")
        print("=" * 60)
        
        # ✅ is_verified চেক করুন
        is_verified = False
        try:
            application = HospitalApplication.objects.get(hospital_admin=request.user)
            is_verified = application.status == 'approved'
            print(f"✅ is_verified: {is_verified}")
            print(f"✅ Application status: {application.status}")
        except HospitalApplication.DoesNotExist:
            print("❌ No HospitalApplication found")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # ✅ সঠিকভাবে হাসপাতাল অ্যাডমিন প্রোফাইল পাওয়া
        try:
            hospital_admin = HospitalAdminProfile.objects.get(user=request.user)
            hospital = hospital_admin.hospital
            print(f"✅ Hospital found: {hospital}")
        except HospitalAdminProfile.DoesNotExist:
            print("❌ HospitalAdminProfile not found")
            messages.error(request, "Hospital Admin profile not found.")
            return redirect('hospital_admin:dashboard')
        except Exception as e:
            print(f"❌ Error: {e}")
            messages.error(request, f"Error: {str(e)}")
            return redirect('hospital_admin:dashboard')
        
        lab_technicians = LabTechnician.objects.filter(
            hospital=hospital
        ).select_related('user')
        
        print(f"✅ Lab Technicians count: {lab_technicians.count()}")
        print("=" * 60)

        context = {
            'lab_technicians': lab_technicians,
            'is_verified': is_verified,
            'page_title': 'Lab Technician Management',
            'current_page': 'Lab Technicians',
        }
        return render(request, self.template_name, context)


@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class LabTechnicianCreateView(View):
    """
    View to create a new lab technician.
    """
    template_name = 'hospital_admin/lab_technicians/create.html'

    def get(self, request):
        # ✅ is_verified চেক করুন
        is_verified = False
        try:
            application = HospitalApplication.objects.get(hospital_admin=request.user)
            is_verified = application.status == 'approved'
        except HospitalApplication.DoesNotExist:
            pass
        
        form = CreateLabTechnicianForm()
        context = {
            'form': form,
            'is_verified': is_verified,  # ✅ যোগ করুন
            'page_title': 'Create Lab Technician',
            'current_page': 'Lab Technicians',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateLabTechnicianForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # ✅ সঠিকভাবে হাসপাতাল অ্যাডমিন প্রোফাইল পাওয়া
                    try:
                        hospital_admin = HospitalAdminProfile.objects.get(user=request.user)
                        hospital = hospital_admin.hospital
                    except HospitalAdminProfile.DoesNotExist:
                        messages.error(request, "Hospital Admin profile not found.")
                        return redirect('hospital_admin:dashboard')
                    
                    lab_technician = form.save(hospital=hospital)
                    
                    messages.success(
                        request,
                        f"Lab Technician '{lab_technician.full_name}' created successfully!"
                    )
                    return redirect('lab_technicians:list')
            except Exception as e:
                messages.error(request, f"Error creating lab technician: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        context = {
            'form': form,
            'page_title': 'Create Lab Technician',
            'current_page': 'Lab Technicians',
        }
        return render(request, self.template_name, context)


@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class LabTechnicianEditView(View):
    """
    View to edit an existing lab technician.
    """
    template_name = 'hospital_admin/lab_technicians/edit.html'

    def get(self, request, pk):
        # ✅ is_verified চেক করুন
        is_verified = False
        try:
            application = HospitalApplication.objects.get(hospital_admin=request.user)
            is_verified = application.status == 'approved'
        except HospitalApplication.DoesNotExist:
            pass
        
        # ✅ সঠিকভাবে হাসপাতাল অ্যাডমিন প্রোফাইল পাওয়া
        try:
            hospital_admin = HospitalAdminProfile.objects.get(user=request.user)
            hospital = hospital_admin.hospital
        except HospitalAdminProfile.DoesNotExist:
            messages.error(request, "Hospital Admin profile not found.")
            return redirect('hospital_admin:dashboard')
        
        lab_technician = get_object_or_404(
            LabTechnician.objects.select_related('user'),
            pk=pk,
            hospital=hospital
        )
        
        form = EditLabTechnicianForm(instance=lab_technician)
        initial_data = {'email': lab_technician.user.email}
        form = EditLabTechnicianForm(instance=lab_technician, initial=initial_data)

        context = {
            'form': form,
            'lab_technician': lab_technician,
            'is_verified': is_verified,  # ✅ যোগ করুন
            'page_title': 'Edit Lab Technician',
            'current_page': 'Lab Technicians',
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        # ✅ is_verified চেক করুন
        is_verified = False
        try:
            application = HospitalApplication.objects.get(hospital_admin=request.user)
            is_verified = application.status == 'approved'
        except HospitalApplication.DoesNotExist:
            pass
        
        # ✅ সঠিকভাবে হাসপাতাল অ্যাডমিন প্রোফাইল পাওয়া
        try:
            hospital_admin = HospitalAdminProfile.objects.get(user=request.user)
            hospital = hospital_admin.hospital
        except HospitalAdminProfile.DoesNotExist:
            messages.error(request, "Hospital Admin profile not found.")
            return redirect('hospital_admin:dashboard')
        
        lab_technician = get_object_or_404(
            LabTechnician.objects.select_related('user'),
            pk=pk,
            hospital=hospital
        )

        form = EditLabTechnicianForm(
            request.POST,
            request.FILES,
            instance=lab_technician
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(
                        request,
                        f"Lab Technician '{lab_technician.full_name}' updated successfully!"
                    )
                    return redirect('lab_technicians:list')
            except Exception as e:
                messages.error(request, f"Error updating lab technician: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        context = {
            'form': form,
            'lab_technician': lab_technician,
            'is_verified': is_verified,  # ✅ যোগ করুন
            'page_title': 'Edit Lab Technician',
            'current_page': 'Lab Technicians',
        }
        return render(request, self.template_name, context)


@method_decorator([login_required, role_required(['hospital_admin'])], name='dispatch')
class LabTechnicianDeleteView(View):
    """
    View to delete a lab technician.
    """
    template_name = 'hospital_admin/lab_technicians/delete.html'

    def get(self, request, pk):
        # ✅ is_verified চেক করুন
        is_verified = False
        try:
            application = HospitalApplication.objects.get(hospital_admin=request.user)
            is_verified = application.status == 'approved'
        except HospitalApplication.DoesNotExist:
            pass
        
        # ✅ সঠিকভাবে হাসপাতাল অ্যাডমিন প্রোফাইল পাওয়া
        try:
            hospital_admin = HospitalAdminProfile.objects.get(user=request.user)
            hospital = hospital_admin.hospital
        except HospitalAdminProfile.DoesNotExist:
            messages.error(request, "Hospital Admin profile not found.")
            return redirect('hospital_admin:dashboard')
        
        lab_technician = get_object_or_404(
            LabTechnician.objects.select_related('user'),
            pk=pk,
            hospital=hospital
        )

        context = {
            'lab_technician': lab_technician,
            'is_verified': is_verified,  # ✅ যোগ করুন
            'page_title': 'Delete Lab Technician',
            'current_page': 'Lab Technicians',
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        # ✅ সঠিকভাবে হাসপাতাল অ্যাডমিন প্রোফাইল পাওয়া
        try:
            hospital_admin = HospitalAdminProfile.objects.get(user=request.user)
            hospital = hospital_admin.hospital
        except HospitalAdminProfile.DoesNotExist:
            messages.error(request, "Hospital Admin profile not found.")
            return redirect('hospital_admin:dashboard')
        
        lab_technician = get_object_or_404(
            LabTechnician.objects.select_related('user'),
            pk=pk,
            hospital=hospital
        )

        try:
            with transaction.atomic():
                user = lab_technician.user
                lab_technician.delete()
                user.delete()
                messages.success(
                    request,
                    f"Lab Technician '{lab_technician.full_name}' deleted successfully!"
                )
        except Exception as e:
            messages.error(request, f"Error deleting lab technician: {str(e)}")

        return redirect('lab_technicians:list')
    
# =============================================================================
# HOSPITAL ADMIN VIEWS (Existing - Keep as is)
# =============================================================================




# =============================================================================
# LAB TECHNICIAN BASE VIEW (NEW)
# =============================================================================

class LabTechBaseView(View):
    """Base view for Lab Technician with authentication check."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to continue.')
            return redirect('accounts:login')
        
        if request.user.role != 'lab_technician':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard:homepage')
        
        # Get technician profile
        try:
            self.technician = request.user.lab_technician_profile
            self.hospital = self.technician.hospital
        except:
            self.technician = None
            self.hospital = None
        
        return super().dispatch(request, *args, **kwargs)


# =============================================================================
# LAB TECHNICIAN DASHBOARD (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class LabTechDashboardView(LabTechBaseView):
    """Lab Technician Dashboard."""
    template_name = 'lab_technicians/dashboard.html'
    
    def get(self, request):
        if not self.hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('dashboard:homepage')
        
        today = timezone.now().date()
        
        # Get orders for this hospital
        orders = LabOrder.objects.filter(hospital=self.hospital)
        
        # Statistics
        pending_orders = orders.filter(status='ordered').count()
        collected_samples = orders.filter(status='collected').count()
        processing_tests = orders.filter(status='processing').count()
        completed_today = orders.filter(status='completed', updated_at__date=today).count()
        total_reports = orders.filter(status='completed').count()
        
        # Recent activity (last 5 orders)
        recent_orders = orders.order_by('-created_at')[:5]
        
        # Recent completed
        recent_completed = orders.filter(status='completed').order_by('-updated_at')[:5]
        
        context = {
            'pending_orders': pending_orders,
            'collected_samples': collected_samples,
            'processing_tests': processing_tests,
            'completed_today': completed_today,
            'total_reports': total_reports,
            'recent_orders': recent_orders,
            'recent_completed': recent_completed,
            'technician': self.technician,
            'page_title': 'Dashboard',
            'current_page': 'Dashboard',
        }
        return render(request, self.template_name, context)


# =============================================================================
# TEST ORDERS LIST (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class TestOrderListView(LabTechBaseView):
    """List all test orders."""
    template_name = 'lab_technicians/test_orders.html'
    
    def get(self, request):
        if not self.hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('dashboard:homepage')
        
        orders = LabOrder.objects.filter(hospital=self.hospital).select_related(
            'patient', 'doctor', 'doctor__user'
        ).prefetch_related('items', 'items__test')
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            orders = orders.filter(
                Q(order_number__icontains=search_query) |
                Q(patient__full_name__icontains=search_query) |
                Q(patient__user__first_name__icontains=search_query) |
                Q(patient__user__last_name__icontains=search_query) |
                Q(doctor__user__first_name__icontains=search_query) |
                Q(doctor__user__last_name__icontains=search_query)
            )
        
        # Status filter
        status_filter = request.GET.get('status', '')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # Sort
        sort_by = request.GET.get('sort', 'newest')
        if sort_by == 'newest':
            orders = orders.order_by('-created_at')
        elif sort_by == 'oldest':
            orders = orders.order_by('created_at')
        elif sort_by == 'status':
            orders = orders.order_by('status')
        
        # Pagination
        paginator = Paginator(orders, 10)
        page = request.GET.get('page', 1)
        
        try:
            orders_page = paginator.page(page)
        except:
            orders_page = paginator.page(1)
        
        # Status counts for filter badges
        status_counts = {
            'ordered': LabOrder.objects.filter(hospital=self.hospital, status='ordered').count(),
            'collected': LabOrder.objects.filter(hospital=self.hospital, status='collected').count(),
            'processing': LabOrder.objects.filter(hospital=self.hospital, status='processing').count(),
            'completed': LabOrder.objects.filter(hospital=self.hospital, status='completed').count(),
        }
        
        context = {
            'orders': orders_page,
            'status_counts': status_counts,
            'search_query': search_query,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'technician': self.technician,
            'page_title': 'Test Orders',
            'current_page': 'Test Orders',
        }
        return render(request, self.template_name, context)


# =============================================================================
# TEST ORDER DETAIL (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class TestOrderDetailView(LabTechBaseView):
    """View test order details."""
    template_name = 'lab_technicians/test_order_detail.html'
    
    def get(self, request, pk):
        if not self.hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('dashboard:homepage')
        
        order = get_object_or_404(
            LabOrder.objects.select_related('patient', 'doctor', 'doctor__user'),
            id=pk,
            hospital=self.hospital
        )
        
        # Get order items with results
        items = LabOrderItem.objects.filter(lab_order=order).select_related('test')
        
        # Check if result exists
        result = LabResult.objects.filter(lab_order=order).first()
        
        context = {
            'order': order,
            'items': items,
            'result': result,
            'technician': self.technician,
            'page_title': 'Test Order Detail',
            'current_page': 'Test Orders',
        }
        return render(request, self.template_name, context)


# =============================================================================
# COLLECT SAMPLE (NEW)
# =============================================================================

@login_required
@role_required(['lab_technician'])
def collect_sample(request, pk):
    """Collect sample for a test order."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('lab_technicians:test_orders')
    
    order = get_object_or_404(LabOrder, id=pk)
    
    if order.status != 'ordered':
        messages.error(request, 'Sample has already been collected or order is not ready.')
        return redirect('lab_technicians:test_order_detail', pk=pk)
    
    with transaction.atomic():
        order.status = 'collected'
        order.collected_at = timezone.now()
        order.collected_by = request.user
        order.save()
        
        # Update items status
        for item in order.items.all():
            item.status = 'collected'
            item.save()
    
    messages.success(request, f'Sample collected successfully for order {order.order_number}.')
    return redirect('lab_technicians:test_order_detail', pk=pk)


# =============================================================================
# START PROCESSING (NEW)
# =============================================================================

@login_required
@role_required(['lab_technician'])
def start_processing(request, pk):
    """Start processing a collected sample."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('lab_technicians:test_orders')
    
    order = get_object_or_404(LabOrder, id=pk)
    
    if order.status != 'collected':
        messages.error(request, 'Sample must be collected before processing.')
        return redirect('lab_technicians:test_order_detail', pk=pk)
    
    with transaction.atomic():
        order.status = 'processing'
        order.processing_started_at = timezone.now()
        order.save()
        
        # Update items status
        for item in order.items.all():
            item.status = 'processing'
            item.save()
    
    messages.success(request, f'Processing started for order {order.order_number}.')
    return redirect('lab_technicians:test_order_detail', pk=pk)


# =============================================================================
# LAB RESULT CREATE (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class LabResultCreateView(LabTechBaseView):
    """Create lab results for a test order."""
    template_name = 'lab_technicians/lab_result_form.html'
    
    def get(self, request, order_id):
        if not self.hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('dashboard:homepage')
        
        order = get_object_or_404(
            LabOrder.objects.select_related('patient', 'doctor'),
            id=order_id,
            hospital=self.hospital
        )
        
        if order.status == 'completed':
            messages.warning(request, 'This order is already completed.')
            return redirect('lab_technicians:test_order_detail', pk=order_id)
        
        # Check if result already exists
        existing_result = LabResult.objects.filter(lab_order=order).first()
        if existing_result:
            messages.info(request, 'Result already exists for this order.')
            return redirect('lab_technicians:test_order_detail', pk=order_id)
        
        # Get order items
        items = LabOrderItem.objects.filter(lab_order=order).select_related('test')
        
        context = {
            'order': order,
            'items': items,
            'technician': self.technician,
            'page_title': 'Enter Lab Results',
            'current_page': 'Test Orders',
        }
        return render(request, self.template_name, context)
    
    def post(self, request, order_id):
        if not self.hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('dashboard:homepage')
        
        order = get_object_or_404(
            LabOrder.objects.select_related('patient', 'doctor'),
            id=order_id,
            hospital=self.hospital
        )
        
        if order.status == 'completed':
            messages.warning(request, 'This order is already completed.')
            return redirect('lab_technicians:test_order_detail', pk=order_id)
        
        # Check if result already exists
        existing_result = LabResult.objects.filter(lab_order=order).first()
        if existing_result:
            messages.info(request, 'Result already exists for this order.')
            return redirect('lab_technicians:test_order_detail', pk=order_id)
        
        result_value = request.POST.get('result_value')
        interpretation = request.POST.get('interpretation', '')
        remarks = request.POST.get('remarks', '')
        report_file = request.FILES.get('report_file')
        
        if not result_value:
            messages.error(request, 'Please enter result value.')
            return redirect('lab_technicians:lab_result_create', order_id=order_id)
        
        try:
            with transaction.atomic():
                # Create lab result
                result = LabResult.objects.create(
                    lab_order=order,
                    patient=order.patient,
                    doctor=order.doctor,
                    test=order.items.first().test if order.items.exists() else None,
                    result_value=result_value,
                    interpretation=interpretation,
                    remarks=remarks,
                    report_file=report_file,
                    performed_by=request.user,
                    result_date=timezone.now()
                )
                
                # Update order status
                order.status = 'completed'
                order.completed_at = timezone.now()
                order.save()
                
                # Update items
                for item in order.items.all():
                    item.status = 'completed'
                    item.result = result_value
                    item.save()
                
                messages.success(request, f'Result saved successfully for order {order.order_number}.')
                return redirect('lab_technicians:test_order_detail', pk=order_id)
                
        except Exception as e:
            messages.error(request, f'Error saving result: {str(e)}')
            return redirect('lab_technicians:lab_result_create', order_id=order_id)


# =============================================================================
# COMPLETED REPORTS (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class CompletedReportListView(LabTechBaseView):
    """List completed reports."""
    template_name = 'lab_technicians/completed_reports.html'
    
    def get(self, request):
        if not self.hospital:
            messages.error(request, 'No hospital associated with your account.')
            return redirect('dashboard:homepage')
        
        # ✅ completed_at এর পরিবর্তে updated_at ব্যবহার করুন
        orders = LabOrder.objects.filter(
            hospital=self.hospital,
            status='completed'
        ).select_related('patient', 'doctor', 'doctor__user').order_by('-updated_at')
        
        # Search
        search_query = request.GET.get('search', '')
        if search_query:
            orders = orders.filter(
                Q(order_number__icontains=search_query) |
                Q(patient__full_name__icontains=search_query) |
                Q(patient__user__first_name__icontains=search_query) |
                Q(patient__user__last_name__icontains=search_query) |
                Q(doctor__user__first_name__icontains=search_query) |
                Q(doctor__user__last_name__icontains=search_query)
            )
        
        # Date filter - updated_at ব্যবহার করুন
        date_filter = request.GET.get('date', '')
        if date_filter:
            from datetime import datetime
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                orders = orders.filter(updated_at__date=date_obj)
            except:
                pass
        
        # Pagination
        paginator = Paginator(orders, 10)
        page = request.GET.get('page', 1)
        
        try:
            orders_page = paginator.page(page)
        except:
            orders_page = paginator.page(1)
        
        context = {
            'orders': orders_page,
            'search_query': search_query,
            'date_filter': date_filter,
            'technician': self.technician,
            'page_title': 'Completed Reports',
            'current_page': 'Completed Reports',
        }
        return render(request, self.template_name, context)


# =============================================================================
# DOWNLOAD REPORT (NEW)
# =============================================================================

@login_required
@role_required(['lab_technician'])
def download_report(request, pk):
    """Download completed report."""
    order = get_object_or_404(LabOrder, id=pk, status='completed')
    
    result = LabResult.objects.filter(lab_order=order).first()
    if not result or not result.report_file:
        messages.error(request, 'No report file found for this order.')
        return redirect('lab_technicians:completed_reports')
    
    response = HttpResponse(result.report_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{order.order_number}_report.pdf"'
    return response


# =============================================================================
# PROFILE VIEW (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class ProfileView(LabTechBaseView):
    """View lab technician profile."""
    template_name = 'lab_technicians/profile.html'
    
    def get(self, request):
        if not self.technician:
            messages.error(request, 'Technician profile not found.')
            return redirect('dashboard:homepage')
        
        context = {
            'technician': self.technician,
            'user': request.user,
            'page_title': 'Profile',
            'current_page': 'Profile',
        }
        return render(request, self.template_name, context)


# =============================================================================
# PROFILE EDIT (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class ProfileEditView(LabTechBaseView):
    """Edit lab technician profile."""
    template_name = 'lab_technicians/profile_edit.html'
    
    def get(self, request):
        if not self.technician:
            messages.error(request, 'Technician profile not found.')
            return redirect('dashboard:homepage')
        
        context = {
            'technician': self.technician,
            'user': request.user,
            'page_title': 'Edit Profile',
            'current_page': 'Profile',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        if not self.technician:
            messages.error(request, 'Technician profile not found.')
            return redirect('dashboard:homepage')
        
        # Update user
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        # Update technician profile
        technician = self.technician
        technician.full_name = request.POST.get('full_name', technician.full_name)
        technician.phone = request.POST.get('phone', technician.phone)
        technician.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('lab_technicians:profile')


# =============================================================================
# SETTINGS VIEW (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class SettingsView(LabTechBaseView):
    """View settings."""
    template_name = 'lab_technicians/settings.html'
    
    def get(self, request):
        context = {
            'technician': self.technician,
            'page_title': 'Settings',
            'current_page': 'Settings',
        }
        return render(request, self.template_name, context)


# =============================================================================
# CHANGE PASSWORD (NEW)
# =============================================================================

@method_decorator([login_required, role_required(['lab_technician'])], name='dispatch')
class ChangePasswordView(LabTechBaseView):
    """Change password."""
    template_name = 'lab_technicians/change_password.html'
    
    def get(self, request):
        context = {
            'technician': self.technician,
            'page_title': 'Change Password',
            'current_page': 'Settings',
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('lab_technicians:change_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('lab_technicians:change_password')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('lab_technicians:change_password')
        
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect('lab_technicians:settings')