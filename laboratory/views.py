# laboratory/views.py
"""
Class-based views for the Laboratory module.

Provides full CRUD for:
- Lab Orders (with inline items)
- Laboratory Tests (catalogue)
- Test Categories
- Lab Result upload (for individual order items)

All views use services.py for business logic and RoleRequiredMixin for RBAC.
"""

import logging
from datetime import datetime, time
from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required


from django.views.generic import TemplateView

import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import base64
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify

from .models import LabOrder, LabOrderItem, LaboratoryTest, TestCategory, LabResult
from .forms import (
    LabOrderForm, LabOrderItemFormSet, LabResultForm,
    LaboratoryTestForm, TestCategoryForm
)
from .services import (
    create_lab_order,
    update_order_status,
    get_order_with_details,
    search_lab_orders,
    filter_lab_orders,
    upload_lab_result,
    verify_lab_result,
    get_dashboard_stats,
)
from accounts.mixins import RoleRequiredMixin

logger = logging.getLogger(__name__)


# ---------- Lab Order Views ----------
class LabOrderListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """
    List view for lab orders with search, filter, and pagination.
    """
    model = LabOrder
    template_name = 'laboratory/laborder_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'lab_technician', 'receptionist']

    def _parse_date_filter(self, value, end_of_day=False):
        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None

        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)

        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed)

        return parsed

    def get_queryset(self):
        queryset = LabOrder.objects.filter(deleted_at__isnull=True)

        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = search_lab_orders(search_query)

        # Filters from GET
        status = self.request.GET.get('status')
        patient_id = self.request.GET.get('patient')
        doctor_id = self.request.GET.get('doctor')
        hospital_id = self.request.GET.get('hospital')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        # Convert to int if provided, otherwise keep as None
        patient_id = int(patient_id) if patient_id not in (None, '') else None
        doctor_id = int(doctor_id) if doctor_id not in (None, '') else None
        hospital_id = int(hospital_id) if hospital_id not in (None, '') else None

        # Parse date strings into timezone-aware datetimes for the service layer
        parsed_date_from = self._parse_date_filter(date_from)
        parsed_date_to = self._parse_date_filter(date_to, end_of_day=True)

        # Apply filters using service
        if not search_query:
            queryset = filter_lab_orders(
                status=status,
                patient_id=patient_id,
                doctor_id=doctor_id,
                hospital_id=hospital_id,
                date_from=parsed_date_from,
                date_to=parsed_date_to,
            )
        else:
            # Additional filters on top of search results
            if status:
                queryset = queryset.filter(status=status)
            if patient_id:
                queryset = queryset.filter(patient_id=patient_id)
            if doctor_id:
                queryset = queryset.filter(doctor_id=doctor_id)
            if hospital_id:
                queryset = queryset.filter(hospital_id=hospital_id)
            if parsed_date_from:
                queryset = queryset.filter(ordered_date__gte=parsed_date_from)
            if parsed_date_to:
                queryset = queryset.filter(ordered_date__lte=parsed_date_to)

        # Role-based filtering
        user = self.request.user
        user_role = getattr(user, 'role', None)
        if user_role == 'doctor':
            # Show only orders where the user is the doctor
            from doctors.models import Doctor
            try:
                doctor = Doctor.objects.get(user=user)
                queryset = queryset.filter(doctor=doctor)
            except Doctor.DoesNotExist:
                queryset = queryset.none()
        elif user_role == 'patient':
            from patients.models import Patient
            try:
                patient = Patient.objects.get(user=user)
                queryset = queryset.filter(patient=patient)
            except Patient.DoesNotExist:
                queryset = queryset.none()
        # For others (admin, hospital admin, lab tech) show all

        # Order by most recent
        return queryset.select_related(
            'patient', 'patient__user',
            'doctor', 'doctor__user',
            'hospital', 'prescription'
        ).prefetch_related('items').order_by('-ordered_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Preserve GET parameters for pagination
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['patient_filter'] = self.request.GET.get('patient', '')
        context['doctor_filter'] = self.request.GET.get('doctor', '')
        context['hospital_filter'] = self.request.GET.get('hospital', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')

        # For dropdowns in filter form
        from patients.models import Patient
        from doctors.models import Doctor
        from hospitals.models import Hospital

        context['patients'] = Patient.objects.filter(is_active=True)
        context['doctors'] = Doctor.objects.filter(is_active=True)
        # Hospital uses 'active' and 'is_deleted' (not 'is_active')
        context['hospitals'] = Hospital.objects.filter(is_deleted=False, active=True)
        context['status_choices'] = LabOrder.Status.choices

        return context


class LabOrderCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """
    Create a new lab order with inline items.
    """
    model = LabOrder
    form_class = LabOrderForm
    template_name = 'laboratory/laborder_form.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = LabOrderItemFormSet(self.request.POST)
        else:
            # Pre-populate with tests? We can leave it empty.
            context['item_formset'] = LabOrderItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']

        if not item_formset.is_valid():
            return self.form_invalid(form)

        try:
            # Extract test IDs from the formset
            test_ids = []
            for item_form in item_formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    test_ids.append(item_form.cleaned_data['test'].id)

            # Use service to create the order
            order = create_lab_order(
                prescription_id=form.cleaned_data['prescription'].id,
                test_ids=test_ids,
                notes=form.cleaned_data.get('notes', ''),
                created_by=self.request.user,
            )
            messages.success(self.request, _('Lab order created successfully.'))
            return redirect('laboratory:order_detail', pk=order.pk)

        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Lab order creation error: {e}", exc_info=True)
            form.add_error(None, _('An unexpected error occurred. Please try again.'))
            return self.form_invalid(form)


class LabOrderUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """
    Update an existing lab order (status, notes, and items).
    """
    model = LabOrder
    form_class = LabOrderForm
    template_name = 'laboratory/laborder_form.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'lab_technician']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        if self.request.POST:
            context['item_formset'] = LabOrderItemFormSet(
                self.request.POST, instance=order
            )
        else:
            context['item_formset'] = LabOrderItemFormSet(instance=order)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']

        if not item_formset.is_valid():
            return self.form_invalid(form)

        # Update the order status (if changed)
        order = cast(LabOrder, self.get_object())
        new_status = form.cleaned_data.get('status')
        if new_status is None:
            form.add_error('status', _('Status is required.'))
            return self.form_invalid(form)

        if order.status != new_status:
            try:
                order = update_order_status(
                    order_id=order.pk,
                    new_status=cast(str, new_status),
                    updated_by=self.request.user,
                )
            except ValidationError as e:
                form.add_error('status', str(e))
                return self.form_invalid(form)

        # Save the form to update notes and other fields
        form.save()

        # Save the item formset
        item_formset.save()

        messages.success(self.request, _('Lab order updated successfully.'))
        return redirect('laboratory:order_detail', pk=order.pk)


class LabOrderDetailView(LoginRequiredMixin, DetailView):
    """
    Display a lab order with all its items and results.
    """
    model = LabOrder
    template_name = 'laboratory/laborder_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        # Use service to fetch with all related data
        order = get_order_with_details(self.kwargs['pk'])
        return order

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        order = self.get_object()
        role = getattr(user, 'role', None)

        # Check permissions for actions
        context['can_edit'] = role in ['super_admin', 'hospital_admin', 'lab_technician']
        context['can_delete'] = role in ['super_admin', 'hospital_admin']
        context['can_upload_result'] = role in ['super_admin', 'hospital_admin', 'lab_technician']
        context['can_verify_result'] = role in ['super_admin', 'hospital_admin', 'doctor']

        # Keep the resolved order available to the template/context.
        context['order'] = order

        return context


class LabOrderDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """
    Soft delete a lab order.
    """
    model = LabOrder
    template_name = 'laboratory/laborder_confirm_delete.html'
    success_url = reverse_lazy('laboratory:order_list')
    allowed_roles = ['super_admin', 'hospital_admin']

    def delete(self, request, *args, **kwargs):
        order = self.get_object()
        # Soft delete via the model's delete() implementation.
        order.delete()
        messages.success(request, _('Lab order deleted successfully.'))
        return redirect(self.get_success_url())


# ---------- Lab Result Upload View ----------
class LabResultUploadView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Upload or edit a lab result for a specific order item.
    """
    allowed_roles = ['super_admin', 'hospital_admin', 'lab_technician']

    def get(self, request, order_pk, item_pk):
        order = get_object_or_404(LabOrder, pk=order_pk, deleted_at__isnull=True)
        item = get_object_or_404(LabOrderItem, pk=item_pk, lab_order=order, deleted_at__isnull=True)
        result, created = LabResult.objects.get_or_create(order_item=item)
        form = LabResultForm(instance=result)
        context = {
            'form': form,
            'order': order,
            'item': item,
            'result': result,
        }
        return render(request, 'laboratory/labresult_form.html', context)

    def post(self, request, order_pk, item_pk):
        order = get_object_or_404(LabOrder, pk=order_pk, deleted_at__isnull=True)
        item = get_object_or_404(LabOrderItem, pk=item_pk, lab_order=order, deleted_at__isnull=True)
        result, created = LabResult.objects.get_or_create(order_item=item)
        form = LabResultForm(request.POST, request.FILES, instance=result)

        if form.is_valid():
            try:
                # Use service to upload/update result
                lab_result = upload_lab_result(
                    order_item_id=item.pk,
                    result=form.cleaned_data['result'],
                    interpretation=form.cleaned_data.get('interpretation', ''),
                    remarks=form.cleaned_data.get('remarks', ''),
                    report_file=form.cleaned_data.get('report_file'),
                    technician=request.user,
                )
                messages.success(request, _('Result uploaded successfully.'))
                return redirect('laboratory:order_detail', pk=order.pk)
            except ValidationError as e:
                form.add_error(None, str(e))
        else:
            # If form is invalid, re-render with errors
            context = {
                'form': form,
                'order': order,
                'item': item,
                'result': result,
            }
            return render(request, 'laboratory/labresult_form.html', context)


# ---------- Laboratory Test Views (Catalogue) ----------
class LaboratoryTestListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = LaboratoryTest
    template_name = 'laboratory/test_list.html'
    context_object_name = 'tests'
    paginate_by = 20
    allowed_roles = ['super_admin', 'hospital_admin', 'lab_technician']

    def get_queryset(self):
        queryset = super().get_queryset().filter(deleted_at__isnull=True)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(test_code__icontains=search) |
                Q(category__name__icontains=search)
            )
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset.select_related('category')


class LaboratoryTestCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = LaboratoryTest
    form_class = LaboratoryTestForm
    template_name = 'laboratory/test_form.html'
    allowed_roles = ['super_admin', 'hospital_admin']


class LaboratoryTestUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = LaboratoryTest
    form_class = LaboratoryTestForm
    template_name = 'laboratory/test_form.html'
    allowed_roles = ['super_admin', 'hospital_admin']


class LaboratoryTestDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = LaboratoryTest
    template_name = 'laboratory/test_confirm_delete.html'
    success_url = reverse_lazy('laboratory:test_list')
    allowed_roles = ['super_admin', 'hospital_admin']


# ---------- Test Category Views ----------
class TestCategoryListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = TestCategory
    template_name = 'laboratory/category_list.html'
    context_object_name = 'categories'
    allowed_roles = ['super_admin', 'hospital_admin', 'lab_technician']


class TestCategoryCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = TestCategory
    form_class = TestCategoryForm
    template_name = 'laboratory/category_form.html'
    allowed_roles = ['super_admin', 'hospital_admin']


class TestCategoryUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = TestCategory
    form_class = TestCategoryForm
    template_name = 'laboratory/category_form.html'
    allowed_roles = ['super_admin', 'hospital_admin']


class TestCategoryDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    model = TestCategory
    template_name = 'laboratory/category_confirm_delete.html'
    success_url = reverse_lazy('laboratory:category_list')
    allowed_roles = ['super_admin', 'hospital_admin']

class LaboratoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "laboratory/dashboard.html"

@login_required
@role_required(['patient'])
def patient_lab_report_list(request):
    """
    Patient-specific laboratory report list.
    Shows only the logged-in patient's own lab results.
    Status is computed from result and verified_at fields.
    """
    patient = request.user.patient_profile

    # Base queryset – only this patient's lab results, excluding soft-deleted
    base_qs = LabResult.objects.filter(
        order_item__lab_order__patient=patient,
        deleted_at__isnull=True
    ).select_related(
        'order_item__lab_order__doctor',
        'order_item__lab_order__hospital',
        'order_item__test',
        'verified_by'
    ).order_by('-created_at')

    # ---------- Statistics ----------
    total = base_qs.count()
    completed = base_qs.filter(result__isnull=False).count()
    pending = base_qs.filter(result__isnull=True, verified_at__isnull=True).count()
    verified = base_qs.filter(verified_at__isnull=False).count()

    # ---------- Search ----------
    search = request.GET.get('search', '')
    if search:
        base_qs = base_qs.filter(
            Q(order_item__test__name__icontains=search) |
            Q(order_item__lab_order__doctor__full_name__icontains=search) |
            Q(order_item__lab_order__hospital__name__icontains=search) |
            Q(order_item__lab_order__order_number__icontains=search)
        ).distinct()

    # ---------- Status filter ----------
    status_filter = request.GET.get('status', '')
    if status_filter == 'completed':
        base_qs = base_qs.filter(result__isnull=False)
    elif status_filter == 'pending':
        base_qs = base_qs.filter(result__isnull=True, verified_at__isnull=True)
    elif status_filter == 'verified':
        base_qs = base_qs.filter(verified_at__isnull=False)
    # 'cancelled' is not supported; you can ignore or add if needed.

    # ---------- Date range ----------
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        base_qs = base_qs.filter(created_at__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(created_at__date__lte=date_to)

    # ---------- Sorting ----------
    sort = request.GET.get('sort', '-created_at')
    allowed_sort = ['created_at', '-created_at', 'order_item__test__name', 'order_item__lab_order__doctor__full_name']
    if sort in allowed_sort:
        base_qs = base_qs.order_by(sort)
    else:
        base_qs = base_qs.order_by('-created_at')

    # ---------- Pagination ----------
    paginator = Paginator(base_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Status choices for the filter dropdown
    status_choices = [
        ('', 'All'),
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
    ]

    context = {
        'page_obj': page_obj,
        'reports': page_obj,
        'total': total,
        'completed': completed,
        'pending': pending,
        'verified': verified,
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
        'patient': patient,
        'current_date': timezone.now(),
        'status_choices': status_choices,
    }
    return render(request, 'laboratory/patient/lab_report_list.html', context)

@login_required
@role_required(['patient'])
def patient_lab_report_detail(request, pk):
    """
    Patient-specific laboratory report detail view.
    Only the patient who owns the report can view it.
    """
    # Fetch the LabResult with all related data
    report = get_object_or_404(
        LabResult.objects.select_related(
            'order_item__lab_order__patient',
            'order_item__lab_order__doctor',
            'order_item__lab_order__hospital',
            'order_item__test',
            'verified_by',
            'technician'
        ).prefetch_related(
            'order_item__lab_order__items'
        ),
        pk=pk,
        deleted_at__isnull=True
    )

    # Security: ensure the logged-in patient owns this report
    patient = request.user.patient_profile
    lab_order = report.order_item.lab_order
    if lab_order.patient != patient:
        raise PermissionDenied(_("You do not have permission to view this report."))

    # Determine status based on result and verification
    if report.verified_at:
        status = 'verified'
        status_display = 'Verified'
    elif report.result:
        status = 'completed'
        status_display = 'Completed'
    else:
        status = 'pending'
        status_display = 'Pending'

    # Build timeline (only using fields that exist)
    timeline = [
        {'stage': 'Order Created', 'date': lab_order.ordered_date, 'icon': 'fa-file-invoice', 'color': 'blue'},
    ]
    if report.created_at:
        timeline.append({'stage': 'Result Entered', 'date': report.created_at, 'icon': 'fa-flask', 'color': 'purple'})
    if report.verified_at:
        timeline.append({'stage': 'Verified', 'date': report.verified_at, 'icon': 'fa-check-double', 'color': 'green'})

    context = {
        'report': report,
        'lab_order': lab_order,
        'patient': patient,
        'status': status,
        'status_display': status_display,
        'timeline': timeline,
        'current_date': timezone.now(),
    }
    return render(request, 'laboratory/patient/lab_report_detail.html', context)

def generate_lab_report_pdf(lab_result):
    """
    Generate a professional laboratory report PDF using ReportLab.
    Returns a BytesIO object.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        spaceAfter=4,
    )
    normal_style = styles['Normal']
    normal_style.fontName = 'Helvetica'
    normal_style.fontSize = 9
    normal_style.leading = 12
    normal_style.alignment = TA_LEFT

    story = []

    # ---------- DATA EXTRACTION ----------
    order_item = lab_result.order_item
    lab_order = order_item.lab_order
    test = order_item.test
    patient = lab_order.patient
    doctor = lab_order.doctor
    hospital = lab_order.hospital

    # ---------- HEADER ----------
    hospital_name = hospital.name if hospital else "NHIMS Hospital"
    hospital_address = hospital.full_address if hospital and hasattr(hospital, 'full_address') else "Dhaka, Bangladesh"
    hospital_phone = hospital.phone if hospital else "+880 1234 567890"
    hospital_email = hospital.email if hospital else "info@nhims.gov.bd"

    header_text = f"""
    <b>{hospital_name}</b><br/>
    {hospital_address}<br/>
    Phone: {hospital_phone} | Email: {hospital_email}
    """
    story.append(Paragraph(header_text, title_style))
    story.append(Paragraph("National Health Information Management System (NHIMS)", subtitle_style))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("LABORATORY REPORT", title_style))
    story.append(Spacer(1, 0.15*inch))

    # ---------- REPORT INFO TABLE ----------
    if lab_result.verified_at:
        status_display = "Verified"
    elif lab_result.result:
        status_display = "Completed"
    else:
        status_display = "Pending"

    data = [
        ["Report Number", lab_order.order_number],
        ["Report Date", lab_result.created_at.strftime("%B %d, %Y")],
        ["Status", status_display],
        ["Verification", "Verified" if lab_result.verified_at else "Not Verified"],
    ]
    t = Table(data, colWidths=[3.5*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 9),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))

    # ---------- PATIENT & DOCTOR TABLES ----------
    age_display = "N/A"
    if patient.date_of_birth:
        today = timezone.now().date()
        born = patient.date_of_birth
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        age_display = f"{age} years"

    patient_data = [
        ["Patient Information", ""],
        ["Name", patient.full_name],
        ["Patient ID", patient.health_id or "N/A"],
        ["Age", age_display],
        ["Gender", patient.get_gender_display() or "N/A"],
        ["Blood Group", patient.blood_group or "N/A"],
        ["Phone", patient.phone or "N/A"],
    ]
    patient_table = Table(patient_data, colWidths=[3*cm, 4.5*cm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 10),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 10),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, -1), 8),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 1), (1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))

    # Doctor table – using only fields that exist
    doctor_specialties = ', '.join([spec.name for spec in doctor.specialties.all()]) if doctor else "N/A"
    doctor_data = [
        ["Doctor Information", ""],
        ["Name", f"Dr. {doctor.full_name}" if doctor else "N/A"],
        ["Specialization", doctor_specialties],
        ["Qualification", doctor.qualification if doctor else "N/A"],
        ["Registration No.", doctor.registration_number if doctor else "N/A"],
    ]
    doctor_table = Table(doctor_data, colWidths=[3*cm, 4.5*cm])
    doctor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 10),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 10),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, -1), 8),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 1), (1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))

    container = Table([[patient_table, doctor_table]], colWidths=[8*cm, 8*cm])
    container.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(container)
    story.append(Spacer(1, 0.2*inch))

    # ---------- HOSPITAL INFORMATION ----------
    hospital_data = [
        ["Hospital Name", hospital_name],
        ["Address", hospital_address],
        ["Phone", hospital_phone],
    ]
    hospital_table = Table(hospital_data, colWidths=[3*cm, 8*cm])
    hospital_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 9),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(hospital_table)
    story.append(Spacer(1, 0.2*inch))

    # ---------- TEST INFORMATION ----------
    test_info = [
        ["Test Name", test.name],
        ["Category", test.category.name if test.category else "N/A"],
        ["Sample Type", test.sample_type or "N/A"],
        ["Report Date", lab_result.created_at.strftime("%B %d, %Y")],
    ]
    test_table = Table(test_info, colWidths=[3*cm, 8*cm])
    test_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 9),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(test_table)
    story.append(Spacer(1, 0.2*inch))

    # ---------- RESULT TABLE ----------
    story.append(Paragraph("Laboratory Result", heading_style))
    result_data = [
        ["Test", "Result", "Reference Range", "Unit", "Interpretation"]
    ]
    # Determine if abnormal
    is_abnormal = lab_result.interpretation and lab_result.interpretation.lower() not in ('normal', 'negative')
    result_row = [
        test.name,
        lab_result.result or "N/A",
        test.normal_range or "N/A",
        test.unit or "N/A",
        lab_result.interpretation or "N/A",
    ]
    if is_abnormal:
        result_row[4] = Paragraph(f"<b>{lab_result.interpretation}</b>", normal_style)
    result_data.append(result_row)

    result_table = Table(result_data, colWidths=[3*cm, 2.5*cm, 3*cm, 2*cm, 3.5*cm])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 0.2*inch))

    # ---------- REMARKS ----------
    if lab_result.remarks or lab_order.notes:
        story.append(Paragraph("Remarks", heading_style))
        if lab_result.remarks:
            story.append(Paragraph(f"<b>Technician Remarks:</b> {lab_result.remarks}", normal_style))
        if lab_order.notes:
            story.append(Paragraph(f"<b>Pathologist Remarks:</b> {lab_order.notes}", normal_style))
        story.append(Spacer(1, 0.15*inch))

    # ---------- VERIFICATION ----------
    story.append(Paragraph("Verification", heading_style))
    verification_data = [
        ["Verified By", lab_result.verified_by.get_full_name() if lab_result.verified_by else "N/A"],
        ["Verification Date", lab_result.verified_at.strftime("%B %d, %Y %H:%M") if lab_result.verified_at else "N/A"],
        ["Verification Status", "Verified" if lab_result.verified_at else "Not Verified"],
    ]
    verification_table = Table(verification_data, colWidths=[3*cm, 8*cm])
    verification_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 9),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(verification_table)
    story.append(Spacer(1, 0.15*inch))

    # ---------- ATTACHMENT NOTE ----------
    if lab_result.report_file:
        story.append(Paragraph("Original laboratory attachment available in NHIMS.", normal_style))
        story.append(Spacer(1, 0.1*inch))

    # ---------- QR CODE ----------
    qr_data = f"NHIMS:LAB:{lab_order.order_number}:{patient.id}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_image = Image(qr_buffer, width=2*cm, height=2*cm)
    qr_table = Table([[qr_image]], colWidths=[2*cm])
    qr_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # ---------- FOOTER ----------
    left_text = f"""
    <b>Doctor Signature</b><br/>
    ______________________________<br/>
    <i>{doctor.full_name if doctor else 'N/A'}</i>
    <br/><br/>
    <b>Laboratory Seal</b><br/>
    (Placeholder)
    """
    left_para = Paragraph(left_text, normal_style)

    footer_container = Table([[left_para, qr_table]], colWidths=[6*cm, 4*cm])
    footer_container.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(footer_container)
    story.append(Spacer(1, 0.15*inch))

    # Bottom line
    footer_text = f"""
    Generated by NHIMS • {timezone.now().strftime("%B %d, %Y %H:%M")} • Report #{lab_order.order_number}
    <br/>
    <i>This is a confidential medical document.</i>
    """
    story.append(Paragraph(footer_text, ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey,
    )))

    doc.build(story)
    buffer.seek(0)
    return buffer

@login_required
@role_required(['patient'])
def patient_download_lab_report_pdf(request, pk):
    report = get_object_or_404(
        LabResult.objects.select_related(
            'order_item__lab_order__patient',
            'order_item__lab_order__doctor',
            'order_item__lab_order__hospital',
            'order_item__test__category',
            'verified_by',
        ),
        pk=pk,
        deleted_at__isnull=True
    )
    patient = request.user.patient_profile
    lab_order = report.order_item.lab_order
    if lab_order.patient != patient:
        raise PermissionDenied(_("You do not have permission to download this report."))

    pdf_buffer = generate_lab_report_pdf(report)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"LabReport-{lab_order.order_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@role_required(['patient'])
def patient_print_lab_report(request, pk):
    """
    Print‑optimized view that automatically triggers the browser print dialog.
    Only the patient who owns the report can print it.
    """
    # Fetch the LabResult with all related data
    report = get_object_or_404(
        LabResult.objects.select_related(
            'order_item__lab_order__patient',
            'order_item__lab_order__doctor',
            'order_item__lab_order__hospital',
            'order_item__test__category',
            'verified_by',
        ),
        pk=pk,
        deleted_at__isnull=True
    )

    # Security: ensure the logged-in patient owns this report
    patient = request.user.patient_profile
    lab_order = report.order_item.lab_order
    if lab_order.patient != patient:
        raise PermissionDenied(_("You do not have permission to print this report."))

    # Generate QR code as base64 for the HTML page
 
    qr_data = f"NHIMS:LAB:{lab_order.order_number}:{patient.id}"
    qr_img = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{qr_base64}"

    # Determine status
    if report.verified_at:
        status_display = "Verified"
    elif report.result:
        status_display = "Completed"
    else:
        status_display = "Pending"

    context = {
        'report': report,
        'lab_order': lab_order,
        'patient': patient,
        'status_display': status_display,
        'qr_image_data': qr_image_data,
        'current_date': timezone.now(),
        'auto_print': True,   # flag to auto-trigger print
    }
    return render(request, 'laboratory/patient/lab_report_print.html', context)

@login_required
@role_required(['patient'])
def patient_lab_history(request):
    """
    Complete laboratory history for a patient.
    Includes statistics, search, filters, pagination, and timeline/table views.
    """
    patient = request.user.patient_profile

    # Base queryset – only this patient's lab results
    base_qs = LabResult.objects.filter(
        order_item__lab_order__patient=patient,
        deleted_at__isnull=True
    ).select_related(
        'order_item__lab_order__doctor',
        'order_item__lab_order__hospital',
        'order_item__test__category',
        'verified_by'
    ).order_by('-created_at')

    # ---------- Statistics ----------
    total = base_qs.count()
    completed = base_qs.filter(result__isnull=False).count()
    pending = base_qs.filter(result__isnull=True, verified_at__isnull=True).count()
    verified = base_qs.filter(verified_at__isnull=False).count()

    # ---------- Search ----------
    search = request.GET.get('search', '')
    if search:
        base_qs = base_qs.filter(
            Q(order_item__test__name__icontains=search) |
            Q(order_item__lab_order__doctor__full_name__icontains=search) |
            Q(order_item__lab_order__hospital__name__icontains=search) |
            Q(order_item__lab_order__order_number__icontains=search)
        ).distinct()

    # ---------- Status filter ----------
    status_filter = request.GET.get('status', '')
    if status_filter == 'completed':
        base_qs = base_qs.filter(result__isnull=False)
    elif status_filter == 'pending':
        base_qs = base_qs.filter(result__isnull=True, verified_at__isnull=True)
    elif status_filter == 'verified':
        base_qs = base_qs.filter(verified_at__isnull=False)

    # ---------- Category filter ----------
    category_filter = request.GET.get('category', '')
    if category_filter:
        base_qs = base_qs.filter(order_item__test__category__name__icontains=category_filter)

    # ---------- Date range ----------
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        base_qs = base_qs.filter(created_at__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(created_at__date__lte=date_to)

    # ---------- Date shortcuts ----------
    period = request.GET.get('period', '')
    today = timezone.now().date()
    if period == 'today':
        base_qs = base_qs.filter(created_at__date=today)
    elif period == 'week':
        week_ago = today - timezone.timedelta(days=7)
        base_qs = base_qs.filter(created_at__date__gte=week_ago)
    elif period == 'month':
        month_ago = today - timezone.timedelta(days=30)
        base_qs = base_qs.filter(created_at__date__gte=month_ago)
    elif period == 'six_months':
        six_months_ago = today - timezone.timedelta(days=180)
        base_qs = base_qs.filter(created_at__date__gte=six_months_ago)
    elif period == 'year':
        year_ago = today - timezone.timedelta(days=365)
        base_qs = base_qs.filter(created_at__date__gte=year_ago)

    # ---------- Sorting ----------
    sort = request.GET.get('sort', '-created_at')
    allowed_sort = [
        'created_at', '-created_at',
        'order_item__test__name',
        'order_item__lab_order__doctor__full_name'
    ]
    if sort in allowed_sort:
        base_qs = base_qs.order_by(sort)
    else:
        base_qs = base_qs.order_by('-created_at')

    # ---------- View mode ----------
    view_mode = request.GET.get('view', 'timeline')  # 'timeline' or 'table'

    # ---------- Pagination ----------
    paginator = Paginator(base_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ---------- Status choices ----------
    status_choices = [
        ('', 'All'),
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
    ]

    # ---------- Categories (from TestCategory) ----------
    from laboratory.models import TestCategory
    categories = TestCategory.objects.filter(is_active=True, deleted_at__isnull=True).values_list('name', flat=True)

    context = {
        'page_obj': page_obj,
        'reports': page_obj,
        'total': total,
        'completed': completed,
        'pending': pending,
        'verified': verified,
        'search': search,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'date_from': date_from,
        'date_to': date_to,
        'period': period,
        'sort': sort,
        'view_mode': view_mode,
        'status_choices': status_choices,
        'categories': categories,
        'patient': patient,
        'current_date': timezone.now(),
    }
    return render(request, 'laboratory/patient/lab_history.html', context)