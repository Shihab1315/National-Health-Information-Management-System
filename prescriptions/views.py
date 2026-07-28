# prescriptions/views.py
"""
Class-based views for the Prescription module.

Includes dashboard, list, create, update, detail, delete (soft), issue,
print, and AJAX appointment auto‑populate views.
Uses services.py for business logic and permissions.py for RBAC.
"""

import logging
from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from accounts.decorators import role_required
from django.utils.timesince import timesince
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
import base64
from io import BytesIO
from django.forms import inlineformset_factory

from .models import Prescription, PrescriptionMedicine
from appointments.models import Appointment
from .forms import PrescriptionForm, PrescriptionMedicineForm
from .services import (
    create_prescription,
    update_prescription,
    issue_prescription,
    complete_prescription,
    cancel_prescription,
    soft_delete_prescription,
    dashboard_statistics,
    search_prescriptions,
    filter_prescriptions,
    filter_prescriptions_by_user,
    get_prescription_or_404,
    get_prescriptions_by_doctor,
    get_prescriptions_by_patient,
)
from .permissions import (
    can_view_prescription_list,
    can_create_prescription,
    can_view_prescription,
    can_update_prescription,
    can_delete_prescription,
    can_issue_prescription,
    can_complete_prescription,
    can_cancel_prescription,
    filter_prescriptions_by_user as permission_filter,
)
from accounts.mixins import RoleRequiredMixin

logger = logging.getLogger(__name__)

import io
import qrcode
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify


# ---------- Custom Mixin for Permission Denied Redirect ----------
class PrescriptionRoleRequiredMixin(RoleRequiredMixin):
    """
    Override RoleRequiredMixin to redirect to home ('/') instead of 'dashboard'
    when permission is denied.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_role(self.allowed_roles):
            messages.error(request, _("You do not have permission to access this page."))
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)


# ---------- Inline Formset for Medicines ----------
PrescriptionMedicineFormSet = inlineformset_factory(
    Prescription,
    PrescriptionMedicine,
    form=PrescriptionMedicineForm,
    extra=1,
    can_delete=True,
    min_num=0,
    max_num=20,
    validate_min=False,
    validate_max=True,
)


# ---------- Dashboard View ----------
class PrescriptionDashboardView(LoginRequiredMixin, PrescriptionRoleRequiredMixin, TemplateView):
    """
    Dashboard view showing prescription statistics and charts.
    """
    template_name = 'prescriptions/dashboard.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'pharmacist']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Statistics (filtered by user's role)
        stats = dashboard_statistics(user=user)
        context['stats'] = stats

        # Recent prescriptions (last 10)
        recent_qs = Prescription.objects.filter(deleted_at__isnull=True)
        recent_qs = filter_prescriptions_by_user(user, recent_qs)
        context['recent_prescriptions'] = recent_qs.select_related(
            'patient', 'doctor', 'appointment'
        ).order_by('-created_at')[:10]

        return context


# ---------- List View ----------
class PrescriptionListView(LoginRequiredMixin, PrescriptionRoleRequiredMixin, ListView):
    """
    Main list view for prescriptions with search, filter, and pagination.
    """
    model = Prescription
    template_name = 'prescriptions/prescription_list.html'
    context_object_name = 'prescriptions'
    paginate_by = 20
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist', 'pharmacist', 'patient']

    def get_queryset(self):
        queryset = Prescription.objects.filter(deleted_at__isnull=True)

        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = search_prescriptions(search_query)

        # Filters from GET
        status = self.request.GET.get('status')
        doctor_id = self.request.GET.get('doctor')
        hospital_id = self.request.GET.get('hospital')
        patient_id = self.request.GET.get('patient')

        date_from_raw = self.request.GET.get('date_from')
        date_to_raw = self.request.GET.get('date_to')
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None

        # Convert to int if provided
        if doctor_id not in (None, ''):
            doctor_id = int(doctor_id)
        else:
            doctor_id = None
        if hospital_id not in (None, ''):
            hospital_id = int(hospital_id)
        else:
            hospital_id = None
        if patient_id not in (None, ''):
            patient_id = int(patient_id)
        else:
            patient_id = None

        # Apply filters using service
        if not search_query:
            queryset = filter_prescriptions(
                status=status,
                doctor_id=doctor_id,
                hospital_id=hospital_id,
                patient_id=patient_id,
                date_from=date_from,
                date_to=date_to,
                is_active=True
            )
        else:
            # Additional filters on top of search results
            if status:
                queryset = queryset.filter(status=status)
            if doctor_id:
                queryset = queryset.filter(doctor_id=doctor_id)
            if hospital_id:
                queryset = queryset.filter(hospital_id=hospital_id)
            if patient_id:
                queryset = queryset.filter(patient_id=patient_id)
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)

        # Role-based filtering
        queryset = filter_prescriptions_by_user(cast(Any, self.request.user), queryset)

        # ★ FIX: Use select_related to fetch patient, doctor, hospital and their users
        queryset = queryset.select_related(
            'patient__user',
            'doctor__user',
            'hospital'
        ).order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Preserve GET parameters for pagination
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['doctor_filter'] = self.request.GET.get('doctor', '')
        context['hospital_filter'] = self.request.GET.get('hospital', '')
        context['patient_filter'] = self.request.GET.get('patient', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')

        # For dropdowns in filter form
        from hospitals.models import Hospital
        from doctors.models import Doctor
        from patients.models import Patient
        context['hospitals'] = Hospital.objects.filter(is_deleted=False, active=True)
        context['doctors'] = Doctor.objects.filter(is_active=True)
        context['patients'] = Patient.objects.filter(is_active=True)
        context['status_choices'] = Prescription.Status.choices

        return context


# ---------- Detail View ----------
class PrescriptionDetailView(LoginRequiredMixin, DetailView):
    """
    Detailed view for a single prescription.
    """
    model = Prescription
    template_name = 'prescriptions/prescription_detail.html'
    context_object_name = 'prescription'

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        obj = cast(Prescription, super().get_object(queryset))
        if not can_view_prescription(cast(Any, self.request.user), obj):
            raise PermissionDenied(_("You do not have permission to view this prescription."))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = cast(Any, self.request.user)
        prescription = context['prescription']
        context['can_edit'] = can_update_prescription(user, prescription)
        context['can_delete'] = can_delete_prescription(user, prescription)
        context['can_issue'] = can_issue_prescription(user, prescription)
        context['can_complete'] = can_complete_prescription(user, prescription)
        context['can_cancel'] = can_cancel_prescription(user, prescription)
        # Prefetch medicines (already done by model's default manager)
        return context


# ---------- Create View ----------
class PrescriptionCreateView(LoginRequiredMixin, PrescriptionRoleRequiredMixin, CreateView):
    """
    Create a new prescription with inline medicines.
    """
    model = Prescription
    form_class = PrescriptionForm
    template_name = 'prescriptions/prescription_create.html'  # ★ Separate create template
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Filter appointment queryset based on user's role
        user = cast(Any, self.request.user)
        if getattr(user, 'role', None) == 'doctor':
            doctor = getattr(user, 'doctor_profile', None)
            if doctor is not None:
                kwargs['appointment_queryset'] = Appointment.objects.filter(
                    doctor=doctor,
                    status=Appointment.Status.COMPLETED,
                    deleted_at__isnull=True,
                    prescription__isnull=True
                ).select_related('patient', 'doctor')
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ★ Added context variables for the base template
        context['title'] = 'Create Prescription'
        context['subtitle'] = 'Generate a new prescription for a completed appointment'
        context['button_text'] = 'Create Prescription'

        if self.request.POST:
            context['medicine_formset'] = PrescriptionMedicineFormSet(self.request.POST)
        else:
            context['medicine_formset'] = PrescriptionMedicineFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        medicine_formset = context['medicine_formset']

        if not medicine_formset.is_valid():
            return self.form_invalid(form)

        try:
            # Extract medicine data from formset
            medicines = []
            for med_form in medicine_formset:
                if med_form.cleaned_data and not med_form.cleaned_data.get('DELETE', False):
                    medicines.append({
                        'medicine_name': med_form.cleaned_data['medicine_name'],
                        'dosage': med_form.cleaned_data['dosage'],
                        'frequency': med_form.cleaned_data['frequency'],
                        'duration': med_form.cleaned_data.get('duration', ''),
                        'route': med_form.cleaned_data['route'],
                        'instruction': med_form.cleaned_data.get('instruction', ''),
                        'before_food': med_form.cleaned_data.get('before_food', False),
                        'after_food': med_form.cleaned_data.get('after_food', False),
                        'morning': med_form.cleaned_data.get('morning', False),
                        'afternoon': med_form.cleaned_data.get('afternoon', False),
                        'night': med_form.cleaned_data.get('night', False),
                        'notes': med_form.cleaned_data.get('notes', ''),
                    })

            # Create prescription via service
            prescription = create_prescription(
                appointment_id=form.cleaned_data['appointment'].id,
                diagnosis=form.cleaned_data['diagnosis'],
                symptoms=form.cleaned_data.get('symptoms', ''),
                clinical_notes=form.cleaned_data.get('clinical_notes', ''),
                advice=form.cleaned_data.get('advice', ''),
                follow_up_date=form.cleaned_data.get('follow_up_date'),
                status=form.cleaned_data['status'],
                created_by=self.request.user,
                medicines=medicines,
            )
            messages.success(self.request, _("Prescription created successfully."))
            return redirect('prescriptions:detail', pk=prescription.pk)

        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Prescription creation error: {e}", exc_info=True)
            form.add_error(None, _("An unexpected error occurred. Please try again."))
            return self.form_invalid(form)


# ---------- Update View ----------
class PrescriptionUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing prescription with inline medicines.
    """
    model = Prescription
    form_class = PrescriptionForm
    template_name = 'prescriptions/prescription_update.html'  # ★ Separate update template
    context_object_name = 'prescription'

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def dispatch(self, request, *args, **kwargs):
        obj = cast(Prescription, self.get_object())
        if not can_update_prescription(cast(Any, request.user), obj):
            raise PermissionDenied(_("You do not have permission to edit this prescription."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        prescription = cast(Prescription, self.get_object())

        # Exclude already used appointments (except current)
        kwargs['appointment_queryset'] = Appointment.objects.filter(
            status=Appointment.Status.COMPLETED,
            deleted_at__isnull=True
        ).exclude(
            prescription__isnull=False
        ).select_related('patient', 'doctor')
        # Add current appointment to queryset if it has prescription
        current = prescription.appointment
        if current:
            kwargs['appointment_queryset'] = kwargs['appointment_queryset'] | Appointment.objects.filter(pk=current.pk)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ★ Added context variables for the base template
        context['title'] = 'Edit Prescription'
        context['subtitle'] = 'Update prescription details'
        context['button_text'] = 'Update Prescription'

        prescription = cast(Prescription, self.get_object())
        if self.request.POST:
            context['medicine_formset'] = PrescriptionMedicineFormSet(
                self.request.POST, instance=prescription
            )
        else:
            context['medicine_formset'] = PrescriptionMedicineFormSet(instance=prescription)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        medicine_formset = context['medicine_formset']
        prescription = self.get_object()

        if not medicine_formset.is_valid():
            return self.form_invalid(form)

        try:
            # Extract medicine data
            medicines = []
            for med_form in medicine_formset:
                if med_form.cleaned_data and not med_form.cleaned_data.get('DELETE', False):
                    medicines.append({
                        'medicine_name': med_form.cleaned_data['medicine_name'],
                        'dosage': med_form.cleaned_data['dosage'],
                        'frequency': med_form.cleaned_data['frequency'],
                        'duration': med_form.cleaned_data.get('duration', ''),
                        'route': med_form.cleaned_data['route'],
                        'instruction': med_form.cleaned_data.get('instruction', ''),
                        'before_food': med_form.cleaned_data.get('before_food', False),
                        'after_food': med_form.cleaned_data.get('after_food', False),
                        'morning': med_form.cleaned_data.get('morning', False),
                        'afternoon': med_form.cleaned_data.get('afternoon', False),
                        'night': med_form.cleaned_data.get('night', False),
                        'notes': med_form.cleaned_data.get('notes', ''),
                    })

            # Update prescription via service
            prescription = update_prescription(
                prescription_id=prescription.pk,
                diagnosis=form.cleaned_data['diagnosis'],
                symptoms=form.cleaned_data.get('symptoms', ''),
                clinical_notes=form.cleaned_data.get('clinical_notes', ''),
                advice=form.cleaned_data.get('advice', ''),
                follow_up_date=form.cleaned_data.get('follow_up_date'),
                status=form.cleaned_data['status'],
                updated_by=self.request.user,
                medicines=medicines,
            )
            messages.success(self.request, _("Prescription updated successfully."))
            return redirect('prescriptions:detail', pk=prescription.pk)

        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Prescription update error: {e}", exc_info=True)
            form.add_error(None, _("An unexpected error occurred. Please try again."))
            return self.form_invalid(form)


# ---------- Delete View (Soft Delete) ----------
class PrescriptionDeleteView(LoginRequiredMixin, DeleteView):
    """
    Soft delete a prescription.
    """
    model = Prescription
    template_name = 'prescriptions/prescription_confirm_delete.html'
    success_url = reverse_lazy('prescriptions:list')

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def dispatch(self, request, *args, **kwargs):
        obj = cast(Prescription, self.get_object())
        if not can_delete_prescription(cast(Any, request.user), obj):
            raise PermissionDenied(_("You do not have permission to delete this prescription."))
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        prescription = self.get_object()
        try:
            soft_delete_prescription(prescription.pk, deleted_by=request.user)
            messages.success(request, _("Prescription deleted successfully."))
            return redirect(self.get_success_url())
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('prescriptions:detail', pk=prescription.pk)
        except Exception:
            messages.error(request, _("An error occurred while deleting the prescription."))
            return redirect('prescriptions:detail', pk=prescription.pk)


# ---------- Quick Action Views (POST) ----------
class PrescriptionIssueView(LoginRequiredMixin, View):
    """Issue a prescription (POST only)."""
    def post(self, request, pk):
        try:
            prescription = get_prescription_or_404(pk)
            if not can_issue_prescription(request.user, prescription):
                raise PermissionDenied(_("You don't have permission to issue this prescription."))
            issue_prescription(pk, issued_by=request.user)
            messages.success(request, _("Prescription issued successfully."))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, _("Error issuing prescription."))
        return redirect('prescriptions:detail', pk=pk)


class PrescriptionCompleteView(LoginRequiredMixin, View):
    """Mark a prescription as completed (POST only)."""
    def post(self, request, pk):
        try:
            prescription = get_prescription_or_404(pk)
            if not can_complete_prescription(request.user, prescription):
                raise PermissionDenied(_("You don't have permission to complete this prescription."))
            complete_prescription(pk, completed_by=request.user)
            messages.success(request, _("Prescription marked as completed."))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, _("Error completing prescription."))
        return redirect('prescriptions:detail', pk=pk)


class PrescriptionCancelView(LoginRequiredMixin, View):
    """Cancel a prescription (POST only)."""
    def post(self, request, pk):
        try:
            prescription = get_prescription_or_404(pk)
            if not can_cancel_prescription(request.user, prescription):
                raise PermissionDenied(_("You don't have permission to cancel this prescription."))
            cancel_prescription(pk, cancelled_by=request.user)
            messages.success(request, _("Prescription cancelled."))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, _("Error cancelling prescription."))
        return redirect('prescriptions:detail', pk=pk)


# ---------- Print View ----------
class PrescriptionPrintView(LoginRequiredMixin, DetailView):
    """
    Display a prescription in print‑friendly format.
    """
    model = Prescription
    template_name = 'prescriptions/prescription_print.html'
    context_object_name = 'prescription'

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        prescription = cast(Prescription, obj)
        if not can_view_prescription(cast(Any, self.request.user), prescription):
            raise PermissionDenied(_("You do not have permission to view this prescription."))
        return prescription


# ---------- AJAX View: Get Appointment Data ----------
class AppointmentDataView(LoginRequiredMixin, View):
    """
    Return appointment data (patient, doctor, hospital) for auto‑population.
    Expects GET parameter: appointment_id.
    """
    def get(self, request):
        appointment_id = request.GET.get('appointment_id')
        if not appointment_id:
            return JsonResponse({'error': 'Missing appointment_id'}, status=400)

        try:
            appointment = Appointment.objects.select_related(
                'patient', 'doctor', 'hospital',
                'patient__user', 'doctor__user'
            ).get(pk=appointment_id, deleted_at__isnull=True)

            # Check if already has prescription (if not, we can allow)
            has_prescription = hasattr(appointment, 'prescription')

            patient_user = appointment.patient.user
            doctor_user = appointment.doctor.user

            data = {
                'id': appointment.pk,
                'patient_name': patient_user.get_full_name() if patient_user else '',
                'patient_id': appointment.patient.pk,
                'doctor_name': doctor_user.get_full_name() if doctor_user else '',
                'doctor_id': appointment.doctor.pk,
                'hospital_name': appointment.hospital.name,
                'hospital_id': appointment.hospital.pk,
                'appointment_number': appointment.appointment_number,
                'appointment_date': appointment.appointment_date.isoformat(),
                'appointment_time': appointment.appointment_time.isoformat(),
                'has_prescription': has_prescription,
                'status': appointment.status,
            }
            return JsonResponse(data)

        except Appointment.DoesNotExist:
            return JsonResponse({'error': 'Appointment not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
@login_required
@role_required(['patient'])
def patient_my_prescriptions(request):
    """
    Patient-specific prescription list view.
    Shows only the logged-in patient's own prescriptions.
    """
    patient = request.user.patient_profile

    # Base queryset – only this patient's prescriptions, excluding draft/cancelled? We'll show all.
    base_qs = Prescription.objects.filter(
        patient=patient
    ).select_related('doctor', 'hospital').order_by('-created_at')

    # ---------- Statistics (unfiltered) ----------
    total = base_qs.count()
    active = base_qs.filter(status=Prescription.Status.ISSUED).count()
    completed = base_qs.filter(status=Prescription.Status.COMPLETED).count()
    expired = base_qs.filter(status=Prescription.Status.CANCELLED).count()  # or any expired logic

    # ---------- Search ----------
    search = request.GET.get('search', '')
    if search:
        # Search in prescription number, doctor name, hospital name, and medicine names
        base_qs = base_qs.filter(
            Q(prescription_number__icontains=search) |
            Q(doctor__full_name__icontains=search) |
            Q(hospital__name__icontains=search) |
            Q(medicines__medicine_name__icontains=search)
        ).distinct()

    # ---------- Status filter ----------
    status_filter = request.GET.get('status', '')
    if status_filter:
        # Map filter value to actual status
        status_map = {
            'active': Prescription.Status.ISSUED,
            'completed': Prescription.Status.COMPLETED,
            'expired': Prescription.Status.CANCELLED,
        }
        if status_filter in status_map:
            base_qs = base_qs.filter(status=status_map[status_filter])

    # ---------- Date range ----------
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        base_qs = base_qs.filter(created_at__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(created_at__date__lte=date_to)

    # ---------- Sorting ----------
    sort = request.GET.get('sort', '-created_at')
    allowed_sort = ['created_at', '-created_at', 'doctor__full_name']
    if sort in allowed_sort:
        base_qs = base_qs.order_by(sort)
    else:
        base_qs = base_qs.order_by('-created_at')

    # ---------- Pagination ----------
    paginator = Paginator(base_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'prescriptions': page_obj,
        'total': total,
        'active': active,
        'completed': completed,
        'expired': expired,
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
        'patient': patient,
        'current_date': timezone.now(),
        'status_choices': Prescription.Status.choices,
    }
    return render(request, 'prescriptions/patient/my_prescriptions.html', context)

@login_required
@role_required(['patient'])
def patient_prescription_detail(request, pk):
    """
    Patient-specific prescription detail view.
    Only the patient who owns the prescription can view it.
    """
    # Fetch the prescription with related data
    prescription = get_object_or_404(
        Prescription.objects.select_related(
            'patient', 'doctor', 'hospital'
        ).prefetch_related(
            'medicines'  # related name for PrescriptionMedicine
        ),
        pk=pk
    )

    # Security: ensure the logged-in patient owns this prescription
    patient = request.user.patient_profile
    if prescription.patient != patient:
        raise PermissionDenied(_("You do not have permission to view this prescription."))

    context = {
        'prescription': prescription,
        'patient': patient,
        'current_date': timezone.now(),
    }
    return render(request, 'prescriptions/patient/prescription_detail.html', context)
def generate_prescription_pdf(prescription):
    """
    Generate a professional medical prescription PDF using ReportLab.
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

    # ---------- HEADER ----------
    hospital = prescription.hospital
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

    story.append(Paragraph("MEDICAL PRESCRIPTION", title_style))
    story.append(Spacer(1, 0.15*inch))

    # ---------- PRESCRIPTION INFO TABLE ----------
    data = [
        ["Prescription Number", prescription.prescription_number],
        ["Date", prescription.created_at.strftime("%B %d, %Y")],
        ["Status", prescription.get_status_display()],
        ["Issued By", f"Dr. {prescription.doctor.full_name}" if prescription.doctor else "N/A"],
    ]
    if hasattr(prescription, 'token') and prescription.token:
        data.append(["Token", prescription.token])

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

    # ---------- PATIENT & DOCTOR TABLES (side by side) ----------
    patient = prescription.patient
    doctor = prescription.doctor

    age_display = "N/A"
    if patient.date_of_birth:
        today = timezone.now().date()
        born = patient.date_of_birth
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        age_display = f"{age} years"

    # Patient table – label column narrower, value column wider to hold text
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

    # Doctor table – wider columns
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

    # ---------- MEDICAL INFORMATION ----------
    story.append(Paragraph("Medical Information", heading_style))
    story.append(Paragraph(f"<b>Diagnosis:</b> {prescription.diagnosis or 'N/A'}", normal_style))
    story.append(Paragraph(f"<b>Symptoms:</b> {prescription.symptoms or 'N/A'}", normal_style))
    story.append(Paragraph(f"<b>Clinical Notes:</b> {prescription.clinical_notes or 'N/A'}", normal_style))
    story.append(Paragraph(f"<b>Doctor's Advice:</b> {prescription.advice or 'N/A'}", normal_style))
    story.append(Spacer(1, 0.15*inch))

    # ---------- MEDICINES TABLE ----------
    medicines = prescription.medicines.all()
    if medicines:
        story.append(Paragraph("Prescribed Medicines", heading_style))
        medicine_data = [["Medicine", "Dosage", "Frequency", "Duration", "Instructions"]]
        for item in medicines:
            medicine_data.append([
                item.medicine_name,
                item.dosage or "—",
                item.frequency or "—",
                item.duration or "—",
                item.instruction or "—",
            ])
        med_table = Table(medicine_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 2*cm, 3.5*cm])
        med_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
        ]))
        story.append(med_table)
        story.append(Spacer(1, 0.2*inch))

    # ---------- FOLLOW-UP ----------
    if prescription.follow_up_date:
        story.append(Paragraph(f"<b>Next Follow-up Date:</b> {prescription.follow_up_date.strftime('%B %d, %Y')}", normal_style))
        review_notes = getattr(prescription, 'review_notes', None) or prescription.advice or 'N/A'
        story.append(Paragraph(f"<b>Review Notes:</b> {review_notes}", normal_style))
        story.append(Spacer(1, 0.15*inch))

    # ---------- FOOTER ----------
    left_text = f"""
    <b>Doctor Signature</b><br/>
    ______________________________<br/>
    <i>{prescription.doctor.full_name if prescription.doctor else 'N/A'}</i>
    <br/><br/>
    <b>Hospital Seal</b><br/>
    (Placeholder)
    """
    left_para = Paragraph(left_text, normal_style)

    # QR Code
    qr_data = f"NHIMS:RX:{prescription.prescription_number}:{prescription.patient.id}"
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

    footer_container = Table([[left_para, qr_table]], colWidths=[6*cm, 4*cm])
    footer_container.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(footer_container)
    story.append(Spacer(1, 0.15*inch))

    footer_text = f"""
    Generated by NHIMS • {timezone.now().strftime("%B %d, %Y %H:%M")} • Prescription #{prescription.prescription_number}
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
def patient_prescription_download(request, pk):
    """
    Download a prescription as a professional PDF.
    Only the patient who owns the prescription can download.
    """
    # Fetch the prescription with related data
    prescription = get_object_or_404(
        Prescription.objects.select_related('patient', 'doctor', 'hospital')
        .prefetch_related('medicines'),
        pk=pk
    )

    # Security: ensure the logged-in patient owns this prescription
    patient = request.user.patient_profile
    if prescription.patient != patient:
        raise PermissionDenied(_("You do not have permission to download this prescription."))

    # Generate the PDF
    pdf_buffer = generate_prescription_pdf(prescription)

    # Create the HTTP response
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"Prescription-{prescription.prescription_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@role_required(['patient'])
def patient_prescription_print(request, pk):
    """
    Dedicated print view that automatically triggers the browser print dialog.
    After printing or cancelling, redirects back to the detail page.
    """
    prescription = get_object_or_404(
        Prescription.objects.select_related(
            'patient', 'doctor', 'hospital'
        ).prefetch_related('medicines'),
        pk=pk
    )

    patient = request.user.patient_profile
    if prescription.patient != patient:
        raise PermissionDenied(_("You do not have permission to view this prescription."))

    # Generate QR code as base64 (reuse logic)
@login_required
@role_required(['patient'])
def patient_prescription_print(request, pk):
    """
    Dedicated print view that automatically triggers the browser print dialog.
    After printing or cancelling, redirects back to the detail page.
    """
    prescription = get_object_or_404(
        Prescription.objects.select_related(
            'patient', 'doctor', 'hospital'
        ).prefetch_related('medicines'),
        pk=pk
    )

    patient = request.user.patient_profile
    if prescription.patient != patient:
        raise PermissionDenied(_("You do not have permission to view this prescription."))

    # Generate QR code as base64 (reuse logic)
    
    qr_data = f"NHIMS:RX:{prescription.prescription_number}:{prescription.patient.id}"
    qr_img = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{qr_base64}"

    context = {
        'prescription': prescription,
        'qr_image_data': qr_image_data,
        'current_date': timezone.now(),
    }
    return render(request, 'prescriptions/patient/prescription_print.html', context)
    qr_data = f"NHIMS:RX:{prescription.prescription_number}:{prescription.patient.id}"
    qr_img = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{qr_base64}"

    context = {
        'prescription': prescription,
        'qr_image_data': qr_image_data,
        'current_date': timezone.now(),
    }
    return render(request, 'prescriptions/patient/prescription_print.html', context)