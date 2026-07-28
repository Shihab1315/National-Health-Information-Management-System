"""
Class-based views for the Appointment module.
"""
from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timesince import timesince
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)

import io
import qrcode
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from django.conf import settings


from accounts.decorators import role_required
from accounts.mixins import RoleRequiredMixin
from doctors.models import Doctor, Specialty
from hospitals.models import Hospital

from .forms import AppointmentForm, PatientAppointmentForm
from .models import Appointment
from .permissions import (
    can_view_appointment,
    can_update_appointment,
    can_cancel_appointment,
    can_confirm_appointment,
    can_complete_appointment,
    can_delete_appointment,
    filter_appointments_by_user,
)
from .services import (
    create_appointment,
    cancel_appointment,
    confirm_appointment,
    complete_appointment,
    dashboard_statistics,
    search_appointments,
    filter_appointments,
    get_upcoming_appointments,
    get_appointment_or_404,
    reschedule_appointment,
    doctor_available,
)

# ---------- Custom Mixin to Fix Redirect ----------
class AppRoleRequiredMixin(RoleRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_role(self.allowed_roles):
            messages.error(request, "You do not have permission to access this page.")
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)


# ---------- Dashboard View ----------
class AppointmentDashboardView(LoginRequiredMixin, AppRoleRequiredMixin, TemplateView):
    template_name = 'appointments/dashboard.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        stats = dashboard_statistics()
        context['stats'] = stats

        user_role = getattr(user, 'role', None)
        if user_role == 'doctor':
            try:
                from doctors.models import Doctor
                doctor = Doctor.objects.get(user=user, is_active=True)
                upcoming = get_upcoming_appointments(doctor_id=doctor.pk, days_ahead=7)
            except Doctor.DoesNotExist:
                upcoming = []
        else:
            upcoming = get_upcoming_appointments(days_ahead=7)

        context['upcoming_appointments'] = upcoming[:10]

        today = timezone.now().date()
        today_qs = filter_appointments(date_from=today, date_to=today)
        today_qs = filter_appointments_by_user(cast(Any, user), today_qs)
        context['today_appointments'] = today_qs[:10]

        return context


# ---------- List Views ----------
class AppointmentListView(LoginRequiredMixin, AppRoleRequiredMixin, ListView):
    model = Appointment
    template_name = 'appointments/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 20
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']

    def get_queryset(self):
        queryset = super().get_queryset().filter(deleted_at__isnull=True)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = search_appointments(search_query)

        status = self.request.GET.get('status')
        date_from_str = self.request.GET.get('date_from')
        date_to_str = self.request.GET.get('date_to')
        date_from = parse_date(date_from_str) if date_from_str else None
        date_to = parse_date(date_to_str) if date_to_str else None

        hospital_id = self.request.GET.get('hospital')
        doctor_id = self.request.GET.get('doctor')
        patient_id = self.request.GET.get('patient')

        if hospital_id not in (None, ''):
            hospital_id = int(hospital_id)
        else:
            hospital_id = None
        if doctor_id not in (None, ''):
            doctor_id = int(doctor_id)
        else:
            doctor_id = None
        if patient_id not in (None, ''):
            patient_id = int(patient_id)
        else:
            patient_id = None

        if not search_query:
            queryset = filter_appointments(
                status=status,
                date_from=date_from,
                date_to=date_to,
                hospital_id=hospital_id,
                doctor_id=doctor_id,
                patient_id=patient_id,
                is_active=True
            )
        else:
            if status:
                queryset = queryset.filter(status=status)
            if date_from:
                queryset = queryset.filter(appointment_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(appointment_date__lte=date_to)
            if hospital_id:
                queryset = queryset.filter(hospital_id=hospital_id)
            if doctor_id:
                queryset = queryset.filter(doctor_id=doctor_id)
            if patient_id:
                queryset = queryset.filter(patient_id=patient_id)

        queryset = filter_appointments_by_user(cast(Any, self.request.user), queryset)

        # ★ Optimize: prefetch related user data for patient and doctor names
        queryset = queryset.select_related('patient__user', 'doctor__user', 'hospital')

        return queryset.order_by('-appointment_date', '-appointment_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['hospital_filter'] = self.request.GET.get('hospital', '')
        context['doctor_filter'] = self.request.GET.get('doctor', '')
        context['patient_filter'] = self.request.GET.get('patient', '')

        from hospitals.models import Hospital
        from doctors.models import Doctor
        from patients.models import Patient

        context['hospitals'] = Hospital.objects.filter(is_deleted=False, active=True)
        context['doctors'] = Doctor.objects.filter(is_active=True)
        context['patients'] = Patient.objects.filter(is_active=True)

        context['status_choices'] = Appointment.Status.choices
        return context


class TodayAppointmentsView(AppointmentListView):
    template_name = 'appointments/today_appointments.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']

    def get_queryset(self):
        today = timezone.now().date()
        return super().get_queryset().filter(appointment_date=today)


class UpcomingAppointmentsView(AppointmentListView):
    template_name = 'appointments/upcoming_appointments.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']

    def get_queryset(self):
        today = timezone.now().date()
        future = today + timezone.timedelta(days=7)
        return super().get_queryset().filter(
            appointment_date__gte=today,
            appointment_date__lte=future
        )


class CompletedAppointmentsView(AppointmentListView):
    template_name = 'appointments/completed_appointments.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']

    def get_queryset(self):
        return super().get_queryset().filter(status=Appointment.Status.COMPLETED)


class CancelledAppointmentsView(AppointmentListView):
    template_name = 'appointments/cancelled_appointments.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']

    def get_queryset(self):
        return super().get_queryset().filter(status=Appointment.Status.CANCELLED)

# ---------- Patient-Specific Appointment List ----------
@login_required
@role_required(["patient"])
def patient_appointment_list(request):
    patient = request.user.patient_profile
    today = timezone.now().date()

    # Base queryset
    base_qs = Appointment.objects.filter(patient=patient).select_related("doctor", "hospital")

    # Search
    search = request.GET.get("search", "")
    if search:
        base_qs = base_qs.filter(
            Q(doctor__user__first_name__icontains=search) |
            Q(doctor__user__last_name__icontains=search) |
            Q(hospital__name__icontains=search) |
            Q(appointment_number__icontains=search)
        )

    # Status filter
    status_filter = request.GET.get("status", "")
    if status_filter:
        base_qs = base_qs.filter(status=status_filter)

    # Date filters
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if date_from:
        base_qs = base_qs.filter(appointment_date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(appointment_date__lte=date_to)

    # Sorting
    sort = request.GET.get("sort", "-appointment_date")
    allowed_sort = ["appointment_date", "-appointment_date", "appointment_time", "doctor__full_name"]
    if sort in allowed_sort:
        base_qs = base_qs.order_by(sort)
    else:
        base_qs = base_qs.order_by("-appointment_date")

    # Statistics (unfiltered)
    all_appointments = Appointment.objects.filter(patient=patient)
    total_appointments = all_appointments.count()
    upcoming_appointments = all_appointments.filter(appointment_date__gte=today).count()
    completed_appointments = all_appointments.filter(status=Appointment.Status.COMPLETED).count()
    cancelled_appointments = all_appointments.filter(status=Appointment.Status.CANCELLED).count()
    pending_appointments = all_appointments.filter(status=Appointment.Status.PENDING).count()

    # Pagination
    paginator = Paginator(base_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "appointments": page_obj,
        "search": search,
        "status_filter": status_filter,
        "date_from": date_from,
        "date_to": date_to,
        "sort": sort,
        "total_appointments": total_appointments,
        "upcoming_appointments": upcoming_appointments,
        "completed_appointments": completed_appointments,
        "cancelled_appointments": cancelled_appointments,
        "pending_appointments": pending_appointments,
        "status_choices": Appointment.Status.choices,
        "patient": patient,
        "current_date": timezone.now(),
    }

    return render(
        request,
        "appointments/patient/appointment_list.html",
        context,
    )
@login_required
@role_required(["patient"])
def patient_appointment_detail(request, pk):
    """
    Patient-specific detail view for an appointment.
    Only the patient who owns the appointment can view it.
    """
    # Get the appointment, ensuring it is not soft-deleted
    appointment = get_object_or_404(Appointment, pk=pk, deleted_at__isnull=True)

    # Check that the logged-in patient is the owner
    patient = request.user.patient_profile
    if appointment.patient != patient:
        raise PermissionDenied(_("You do not have permission to view this appointment."))

    # Additional context for the template (if needed)
    context = {
        'appointment': appointment,
        'current_date': timezone.now(),
        'can_download_slip': appointment.is_confirmed or appointment.is_completed,
        # You can add more context flags here
    }

    return render(request, 'appointments/patient/appointment_detail.html', context)
# ---------- Detail View ----------
class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = 'appointments/appointment_detail.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not can_view_appointment(cast(Any, self.request.user), cast(Appointment, obj)):
            raise PermissionDenied(_("You do not have permission to view this appointment."))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = cast(Any, self.request.user)
        appointment = context['appointment']
        context['can_edit'] = can_update_appointment(user, appointment)
        context['can_delete'] = can_delete_appointment(user, appointment)
        context['can_cancel'] = can_cancel_appointment(user, appointment)
        context['can_confirm'] = can_confirm_appointment(user, appointment)
        context['can_complete'] = can_complete_appointment(user, appointment)
        return context


# ---------- Create View ----------
class AppointmentCreateView(LoginRequiredMixin, AppRoleRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_create.html'
    allowed_roles = ['super_admin', 'hospital_admin', 'doctor', 'receptionist']

    def form_valid(self, form):
        try:
            appointment = create_appointment(
                hospital_id=form.cleaned_data['hospital'].id,
                doctor_id=form.cleaned_data['doctor'].id,
                patient_id=form.cleaned_data['patient'].id,
                appointment_date=form.cleaned_data['appointment_date'],
                appointment_time=form.cleaned_data['appointment_time'],
                reason=form.cleaned_data.get('reason', ''),
                created_by=self.request.user,
            )
            messages.success(self.request, _("Appointment created successfully."))
            return redirect('appointments:detail', pk=appointment.pk)
        except ValidationError as e:
            form.add_error(None, str(e))
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            form.add_error(None, _("An unexpected error occurred. Please try again."))
            messages.error(self.request, _("An unexpected error occurred. Please try again."))
            return self.form_invalid(form)


# ---------- Update View ----------
class AppointmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not can_update_appointment(cast(Any, request.user), obj):
            raise PermissionDenied(_("You do not have permission to edit this appointment."))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            appointment = cast(Appointment, self.get_object())
            new_date = form.cleaned_data['appointment_date']
            new_time = form.cleaned_data['appointment_time']

            if appointment.appointment_date != new_date or appointment.appointment_time != new_time:
                try:
                    reschedule_appointment(
                        appointment.pk,
                        new_date,
                        new_time,
                        rescheduled_by=self.request.user
                    )
                except ValidationError as e:
                    messages.error(self.request, str(e))
                    return self.form_invalid(form)

            appointment.reason = form.cleaned_data['reason']

            new_status = form.cleaned_data['status']
            if appointment.status != new_status:
                if new_status == Appointment.Status.CONFIRMED:
                    confirm_appointment(appointment.pk, confirmed_by=self.request.user)
                elif new_status == Appointment.Status.CANCELLED:
                    cancel_appointment(appointment.pk, cancelled_by=self.request.user)
                elif new_status == Appointment.Status.COMPLETED:
                    complete_appointment(appointment.pk, completed_by=self.request.user)
                else:
                    appointment.status = new_status
                    appointment.save(update_fields=['status'])

            messages.success(self.request, _("Appointment updated successfully."))
            return redirect('appointments:detail', pk=appointment.pk)

        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception:
            messages.error(self.request, _("An error occurred while updating the appointment."))
            return self.form_invalid(form)


# ---------- Delete View ----------
class AppointmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Appointment
    template_name = 'appointments/appointment_confirm_delete.html'
    success_url = reverse_lazy('appointments:list')

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not can_delete_appointment(cast(Any, request.user), cast(Appointment, obj)):
            raise PermissionDenied(_("You do not have permission to delete this appointment."))
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        appointment = self.get_object()
        try:
            Appointment.objects.filter(pk=appointment.pk).update(deleted_at=timezone.now())
            messages.success(request, _("Appointment deleted successfully."))
            return redirect(self.get_success_url())
        except Exception:
            messages.error(request, _("An error occurred while deleting the appointment."))
            return redirect('appointments:detail', pk=appointment.pk)


# ---------- Quick Action Views ----------
class AppointmentConfirmView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            appointment = get_appointment_or_404(pk)
            if not can_confirm_appointment(request.user, appointment):
                raise PermissionDenied(_("You don't have permission to confirm this appointment."))
            confirm_appointment(pk, confirmed_by=request.user)
            messages.success(request, _("Appointment confirmed."))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, _("Error confirming appointment."))
        return redirect('appointments:detail', pk=pk)


class AppointmentCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            appointment = get_appointment_or_404(pk)
            if not can_cancel_appointment(request.user, appointment):
                raise PermissionDenied(_("You don't have permission to cancel this appointment."))
            cancel_appointment(pk, cancelled_by=request.user)
            messages.success(request, _("Appointment cancelled."))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, _("Error cancelling appointment."))
        return redirect('appointments:detail', pk=pk)


class AppointmentCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            appointment = get_appointment_or_404(pk)
            if not can_complete_appointment(request.user, appointment):
                raise PermissionDenied(_("You don't have permission to complete this appointment."))
            complete_appointment(pk, completed_by=request.user)
            messages.success(request, _("Appointment marked as completed."))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, _("Error completing appointment."))
        return redirect('appointments:detail', pk=pk)


# ---------- AJAX Endpoints ----------
class DoctorAvailabilityView(LoginRequiredMixin, View):
    def get(self, request):
        doctor_id_str = request.GET.get('doctor_id')
        date_str = request.GET.get('date')
        time_str = request.GET.get('time')

        if not all([doctor_id_str, date_str, time_str]):
            return JsonResponse({'available': False, 'error': 'Missing parameters'}, status=400)

        try:
            doctor_id = int(doctor_id_str)
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
            time = timezone.datetime.strptime(time_str, '%H:%M').time()
            available = doctor_available(doctor_id, date, time)
            return JsonResponse({'available': available})
        except ValueError:
            return JsonResponse({'available': False, 'error': 'Invalid date/time format'}, status=400)
        except Exception:
            return JsonResponse({'available': False, 'error': 'Server error'}, status=500)


def doctors_by_hospital(request):
    from django.http import JsonResponse
    from doctors.models import Doctor

    hospital_id = request.GET.get('hospital_id')
    if not hospital_id:
        return JsonResponse({'doctors': []})

    try:
        hospital_id = int(hospital_id)
    except ValueError:
        return JsonResponse({'doctors': []})

    doctors = Doctor.objects.filter(
        hospital_id=hospital_id,
        is_active=True
    ).select_related('user')

    data = [
        {'id': doc.pk, 'name': doc.user.get_full_name() if doc.user else f"Dr. {doc.pk}"}
        for doc in doctors
    ]
    return JsonResponse({'doctors': data})
@login_required
@role_required(["patient"])
def patient_book_appointment(request):
    """
    Step-by-step booking wizard for patients.
    GET: Show the booking form.
    POST: Create the appointment.
    """
    print("===== BOOKING VIEW CALLED =====")
    patient = request.user.patient_profile

    if request.method == 'POST':
        form = PatientAppointmentForm(request.POST)
        if form.is_valid():
            try:
                appointment = create_appointment(
                    hospital_id=form.cleaned_data['hospital'].id,
                    doctor_id=form.cleaned_data['doctor'].id,
                    patient_id=patient.id,
                    appointment_date=form.cleaned_data['appointment_date'],
                    appointment_time=form.cleaned_data['appointment_time'],
                    reason=form.cleaned_data.get('reason', ''),
                    created_by=request.user,
                )
                messages.success(request, _("Appointment booked successfully!"))
                return redirect('appointments:patient_appointment_detail', pk=appointment.pk)
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, _("An unexpected error occurred. Please try again."))
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = PatientAppointmentForm()

    hospitals = Hospital.objects.filter(is_deleted=False, active=True)
    # Departments: use the Specialty model if available
    from doctors.models import Specialty
    departments = Specialty.objects.filter(is_active=True).values_list('name', flat=True)

    context = {
        'form': form,
        'patient': patient,
        'hospitals': hospitals,
        'departments': departments,
    }
    return render(request, 'appointments/patient/book_appointment.html', context)
# ---------- Patient Cancel Appointment ----------
@login_required
@role_required(["patient"])
def patient_cancel_appointment(request, pk):
    """
    Patient-specific cancel view with confirmation form and reason.
    Only the patient who owns the appointment can cancel it.
    Only pending or confirmed appointments can be cancelled.
    """
    appointment = get_object_or_404(Appointment, pk=pk, deleted_at__isnull=True)
    patient = request.user.patient_profile

    # Ownership check
    if appointment.patient != patient:
        raise PermissionDenied(_("You are not allowed to cancel this appointment."))

    # Check if cancellation is allowed
    if not (appointment.is_pending() or appointment.is_confirmed()):
        messages.error(request, _("This appointment can no longer be cancelled."))
        return redirect('appointments:patient_appointment_detail', pk=appointment.pk)

    # Check if the appointment date/time has already passed
    now = timezone.now()
    if appointment.appointment_date < now.date() or (
        appointment.appointment_date == now.date() and appointment.appointment_time <= now.time()
    ):
        messages.error(request, _("This appointment has already passed and cannot be cancelled."))
        return redirect('appointments:patient_appointment_detail', pk=appointment.pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        other_text = request.POST.get('other_text', '')

        # Validate reason
        if reason == 'other' and not other_text.strip():
            messages.error(request, _("Please provide additional details for 'Other' reason."))
            return render(request, 'appointments/patient/cancel_appointment.html', {
                'appointment': appointment,
                'errors': {'other_text': 'This field is required when "Other" is selected.'}
            })

        cancellation_note = other_text if reason == 'other' else reason

        try:
            # Use the existing service to cancel
            cancel_appointment(
                appointment.pk,
                cancelled_by=request.user,
            )
            messages.success(request, _("Your appointment has been cancelled successfully."))
            # Optionally create a notification
            # Notification.objects.create(...)
            return redirect('appointments:patient_appointment_detail', pk=appointment.pk)
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, _("An error occurred while cancelling the appointment. Please try again."))

    # GET request: show the confirmation form
    return render(request, 'appointments/patient/cancel_appointment.html', {'appointment': appointment})
# ---------- Patient Reschedule Appointment ----------
@login_required
@role_required(["patient"])
def patient_reschedule_appointment(request, pk):
    """
    Patient-specific reschedule view with step-by-step wizard.
    Only pending or confirmed appointments can be rescheduled.
    """
    appointment = get_object_or_404(Appointment, pk=pk, deleted_at__isnull=True)
    patient = request.user.patient_profile

    # Ownership check
    if appointment.patient != patient:
        raise PermissionDenied(_("You are not allowed to reschedule this appointment."))

    # Check if rescheduling is allowed
    if not (appointment.is_pending() or appointment.is_confirmed()):
        messages.error(request, _("This appointment can no longer be rescheduled."))
        return redirect('appointments:patient_appointment_detail', pk=appointment.pk)

    # Check if the appointment date/time has already passed
    now = timezone.now()
    if appointment.appointment_date < now.date() or (
        appointment.appointment_date == now.date() and appointment.appointment_time <= now.time()
    ):
        messages.error(request, _("This appointment has already passed and cannot be rescheduled."))
        return redirect('appointments:patient_appointment_detail', pk=appointment.pk)

    if request.method == 'POST':
        new_date_str = request.POST.get('new_date')
        new_time_str = request.POST.get('new_time')
        reason = request.POST.get('reason', '')
        other_text = request.POST.get('other_text', '')

        # Validate date and time
        if not new_date_str or not new_time_str:
            messages.error(request, _("Please select a new date and time."))
            return render(request, 'appointments/patient/reschedule_appointment.html', {
                'appointment': appointment,
                'errors': {'date_time': 'Both date and time are required.'}
            })

        try:
            new_date = timezone.datetime.strptime(new_date_str, '%Y-%m-%d').date()
            new_time = timezone.datetime.strptime(new_time_str, '%H:%M').time()
        except ValueError:
            messages.error(request, _("Invalid date or time format."))
            return render(request, 'appointments/patient/reschedule_appointment.html', {'appointment': appointment})

        # Validate reason
        if reason == 'other' and not other_text.strip():
            messages.error(request, _("Please provide additional details for 'Other' reason."))
            return render(request, 'appointments/patient/reschedule_appointment.html', {
                'appointment': appointment,
                'errors': {'other_text': 'This field is required when "Other" is selected.'}
            })

        # Prepare reschedule reason note
        reason_text = other_text if reason == 'other' else reason
        reason_choices = getattr(Appointment, 'ReasonChoices', None)
        if reason_choices:
            reason_text = dict(reason_choices).get(reason, reason)

        try:
            # Use the existing reschedule service
            reschedule_appointment(
                appointment.pk,
                new_date,
                new_time,
                rescheduled_by=request.user
            )
            # Optionally store the reason in notes (if the service doesn't handle it)
            # We can update notes manually
            if reason_text:
                setattr(appointment, 'notes', f"Rescheduled due to: {reason_text}\n{getattr(appointment, 'notes', '') or ''}")
                appointment.save(update_fields=['notes'])

            messages.success(request, _("Your appointment has been rescheduled successfully."))
            return redirect('appointments:patient_appointment_detail', pk=appointment.pk)
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, _("An error occurred while rescheduling. Please try again."))

    # GET: show the reschedule form
    # Generate available slots for the current doctor (we'll use AJAX, but we can pre-fill if needed)
    return render(request, 'appointments/patient/reschedule_appointment.html', {
        'appointment': appointment,
        'patient': patient,
        # 'current_date': timezone.now(),
    })
    
# ---------- Patient Appointment History ----------
@login_required
@role_required(["patient"])
def patient_appointment_history(request):
    """
    Complete appointment history for a patient.
    Includes statistics, search, filters, sorting, pagination, and timeline view.
    """
    patient = request.user.patient_profile
    today = timezone.now().date()

    # Base queryset – all appointments for this patient (including soft-deleted? we exclude deleted)
    base_qs = Appointment.objects.filter(
        patient=patient,
        deleted_at__isnull=True
    ).select_related('doctor', 'hospital')

    # ---------- Statistics (unfiltered) ----------
    total = base_qs.count()
    completed = base_qs.filter(status=Appointment.Status.COMPLETED).count()
    cancelled = base_qs.filter(status=Appointment.Status.CANCELLED).count()
    pending = base_qs.filter(status=Appointment.Status.PENDING).count()
    confirmed = base_qs.filter(status=Appointment.Status.CONFIRMED).count()
    # Rescheduled: those with rescheduled_at not null (we need to check field exists)
    rescheduled = base_qs.filter(rescheduled_at__isnull=False).count() if hasattr(Appointment, 'rescheduled_at') else 0
    # Upcoming: appointments with date >= today and status not cancelled/completed
    upcoming = base_qs.filter(
        appointment_date__gte=today,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
    ).count()

    # ---------- Apply filters ----------
    # Search
    search = request.GET.get('search', '')
    if search:
        base_qs = base_qs & search_appointments(search)

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        base_qs = base_qs.filter(status=status_filter)

    # Date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        base_qs = base_qs.filter(appointment_date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(appointment_date__lte=date_to)

    # Hospital filter
    hospital_id = request.GET.get('hospital', '')
    if hospital_id:
        base_qs = base_qs.filter(hospital_id=hospital_id)

    # Doctor filter
    doctor_id = request.GET.get('doctor', '')
    if doctor_id:
        base_qs = base_qs.filter(doctor_id=doctor_id)

    # Year/Month filter
    year = request.GET.get('year', '')
    month = request.GET.get('month', '')
    if year:
        base_qs = base_qs.filter(appointment_date__year=year)
    if month:
        base_qs = base_qs.filter(appointment_date__month=month)

    # Upcoming/Past/Today shortcuts
    period = request.GET.get('period', '')
    if period == 'today':
        base_qs = base_qs.filter(appointment_date=today)
    elif period == 'upcoming':
        base_qs = base_qs.filter(appointment_date__gte=today)
    elif period == 'past':
        base_qs = base_qs.filter(appointment_date__lt=today)

    # ---------- Sorting ----------
    sort = request.GET.get('sort', '-appointment_date')
    allowed_sort = [
        'appointment_date', '-appointment_date',
        'appointment_time', '-appointment_time',
        'doctor__full_name', '-doctor__full_name',
        'hospital__name', '-hospital__name',
        'status', '-status',
        'created_at', '-created_at'
    ]
    if sort in allowed_sort:
        base_qs = base_qs.order_by(sort)
    else:
        base_qs = base_qs.order_by('-appointment_date')

    # ---------- Pagination ----------
    paginator = Paginator(base_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ---------- Context for filters (dropdowns) ----------
    from hospitals.models import Hospital
    from doctors.models import Doctor

    hospitals = Hospital.objects.filter(is_deleted=False, active=True)
    doctors = Doctor.objects.filter(is_active=True)
    years = Appointment.objects.filter(patient=patient).dates('appointment_date', 'year', order='DESC')
    months = range(1, 13)

    # Determine if we show timeline view (default list)
    view_mode = request.GET.get('view', 'list')  # 'list' or 'timeline'

    context = {
        'page_obj': page_obj,
        'appointments': page_obj,
        'total': total,
        'completed': completed,
        'cancelled': cancelled,
        'pending': pending,
        'confirmed': confirmed,
        'rescheduled': rescheduled,
        'upcoming': upcoming,
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'hospital_filter': hospital_id,
        'doctor_filter': doctor_id,
        'year_filter': year,
        'month_filter': month,
        'period_filter': period,
        'sort': sort,
        'view_mode': view_mode,
        'hospitals': hospitals,
        'doctors': doctors,
        'years': years,
        'months': months,
        'patient': patient,
        'current_date': timezone.now(),
        'status_choices': Appointment.Status.choices,
    }
    return render(request, 'appointments/patient/appointment_history.html', context)

# ---------- PDF Generation Helpers ----------
def generate_appointment_slip_pdf(appointment, request):
    """
    Generate a professional appointment slip PDF using ReportLab.
    """
    from django.utils import timezone

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        spaceAfter=6
    )
    normal_style = styles['Normal']
    normal_style.fontName = 'Helvetica'
    normal_style.fontSize = 10
    normal_style.leading = 14

    story = []

    # ---------- Hospital Header ----------
    hospital = appointment.hospital
    hospital_name = hospital.name if hospital else "NHIMS Hospital"
    hospital_address = hospital.full_address if hospital and hasattr(hospital, 'full_address') else "Dhaka, Bangladesh"
    hospital_phone = hospital.phone if hospital else "+880 1234 567890"
    hospital_email = hospital.email if hospital else "info@nhims.gov.bd"
    emergency_phone = getattr(hospital, 'emergency_phone', None) or hospital_phone

    header_text = f"""
    <b>{hospital_name}</b><br/>
    {hospital_address}<br/>
    Phone: {hospital_phone} | Email: {hospital_email}<br/>
    <b>National Health Information Management System (NHIMS)</b>
    """
    story.append(Paragraph(header_text, title_style))
    story.append(Spacer(1, 0.25*inch))

    # ---------- Title ----------
    story.append(Paragraph("APPOINTMENT SLIP", title_style))
    story.append(Spacer(1, 0.2*inch))

    # ---------- Appointment Info Table ----------
    data = [
        ["Appointment Number", appointment.appointment_number],
        ["Token Number", appointment.token or "N/A"],
        ["Status", appointment.get_status_display()],
        ["Date", appointment.appointment_date.strftime("%A, %B %d, %Y")],
        ["Time", appointment.appointment_time.strftime("%I:%M %p")],
        ["Booking Date", appointment.created_at.strftime("%B %d, %Y %H:%M")],
    ]
    t = Table(data, colWidths=[4*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))

    # ---------- Patient & Doctor Tables ----------
    patient = appointment.patient
    doctor = appointment.doctor

    # Doctor specialties as comma-separated string
    doctor_specialties = ', '.join([spec.name for spec in doctor.specialties.all()]) if doctor else "N/A"
    doctor_qualification = doctor.qualification if doctor else "N/A"
    from datetime import date
    def calculate_age(dob):
        today = date.today()
        return today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )

    patient_data = [
        ["Patient Information", ""],
        ["Name", patient.full_name],
        ["Patient ID", patient.health_id or "N/A"],
        ["Gender", patient.get_gender_display()],
        ["Age", calculate_age(patient.date_of_birth) if patient.date_of_birth else "N/A"],
        ["Blood Group", patient.blood_group or "N/A"],
        ["Phone", patient.phone or "N/A"],
        ["Email", patient.email or "N/A"],
    ]
    patient_table = Table(patient_data, colWidths=[3.5*cm, 5.5*cm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 11),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 11),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, -1), 9),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 1), (1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    doctor_data = [
        ["Doctor Information", ""],
        ["Name", f"Dr. {doctor.full_name}" if doctor else "N/A"],
        ["Specialization", doctor_specialties],
        ["Qualification", doctor_qualification],
        # ["Room", doctor.room_number or "N/A" if doctor else "N/A"],
        ["Consultation Fee", f"${doctor.consultation_fee}" if doctor and doctor.consultation_fee else "N/A"],
    ]
    doctor_table = Table(doctor_data, colWidths=[3.5*cm, 5.5*cm])
    doctor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 11),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 11),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, -1), 9),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 1), (1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    table_container = Table([[patient_table, doctor_table]], colWidths=[5*cm, 5*cm])
    table_container.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(table_container)
    story.append(Spacer(1, 0.2*inch))

    # ---------- Reason (only if exists) ----------
    if appointment.reason:
        story.append(Paragraph("Reason for Visit", heading_style))
        story.append(Paragraph(appointment.reason, normal_style))
        story.append(Spacer(1, 0.1*inch))

    # ---------- QR Code ----------
    qr_data = f"NHIMS:{appointment.appointment_number}:{appointment.patient.id}:{appointment.doctor.id}:{appointment.appointment_date}:{appointment.appointment_time}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, kind='PNG')
    qr_buffer.seek(0)
    qr_image = Image(qr_buffer, width=2*cm, height=2*cm)
    qr_image.hAlign = 'RIGHT'
    story.append(qr_image)
    story.append(Spacer(1, 0.1*inch))

    # ---------- Footer ----------
    footer_text = f"""
    <b>Emergency:</b> {emergency_phone} &nbsp;|&nbsp;
    <b>Terms:</b> Please arrive 15 minutes before the scheduled time. Bring this slip and your ID.
    <br/>
    <i>Generated by NHIMS • {timezone.now().strftime("%B %d, %Y %H:%M")}</i>
    """
    story.append(Paragraph(footer_text, normal_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------- Views ----------
@login_required
@role_required(["patient"])
def patient_appointment_slip_preview(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, deleted_at__isnull=True)
    if appointment.patient != request.user.patient_profile:
        raise PermissionDenied

    # Generate QR code as base64 for HTML preview
    import qrcode
    import base64
    from io import BytesIO
    qr_data = f"NHIMS:{appointment.appointment_number}:{appointment.patient.id}:{appointment.doctor.id}:{appointment.appointment_date}:{appointment.appointment_time}"
    qr_img = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{qr_base64}"

    return render(request, 'appointments/patient/appointment_slip.html', {
        'appointment': appointment,
        'current_date': timezone.now(),
        'qr_image_data': qr_image_data,
    })

@login_required
@role_required(["patient"])
def patient_appointment_slip_pdf(request, pk):
    """Generate and return the appointment slip PDF."""
    appointment = get_object_or_404(Appointment, pk=pk, deleted_at__isnull=True)
    if appointment.patient != request.user.patient_profile:
        raise PermissionDenied

    pdf_buffer = generate_appointment_slip_pdf(appointment, request)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"Appointment_Slip_{appointment.appointment_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@role_required(["patient"])
def patient_appointment_slip_print(request, pk):
    """
    Print‑optimized view that automatically triggers the browser print dialog.
    """
    appointment = get_object_or_404(Appointment, pk=pk, deleted_at__isnull=True)
    if appointment.patient != request.user.patient_profile:
        raise PermissionDenied

    # Generate QR code as base64 for HTML preview
    import qrcode
    import base64
    from io import BytesIO
    qr_data = f"NHIMS:{appointment.appointment_number}:{appointment.patient.id}:{appointment.doctor.id}:{appointment.appointment_date}:{appointment.appointment_time}"
    qr_img = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{qr_base64}"

    return render(request, 'appointments/patient/appointment_slip.html', {
        'appointment': appointment,
        'current_date': timezone.now(),
        'qr_image_data': qr_image_data,
        'auto_print': True,   # ← flag to auto‑trigger print
    })
# ---------- AJAX: Doctors by Hospital & Department ----------
def get_doctors_ajax(request):
    hospital_id = request.GET.get('hospital_id')
    if not hospital_id:
        return JsonResponse({'doctors': []})

    doctors = Doctor.objects.filter(hospital_id=hospital_id, is_active=True)
    data = [{
        'id': doc.pk,
        'full_name': doc.full_name,
        'specialty': ', '.join([spec.name for spec in doc.specialties.all()]),
        'experience': doc.experience,
        'consultation_fee': str(doc.consultation_fee),
        'hospital': doc.hospital.name if doc.hospital else '',
    } for doc in doctors]
    return JsonResponse({'doctors': data})


# ---------- AJAX: Available Dates ----------
def get_available_dates_ajax(request):
    doctor_id = request.GET.get('doctor_id')
    if not doctor_id:
        return JsonResponse({'dates': []})

    # Get the doctor's existing appointments (excluding cancelled)
    existing_dates = Appointment.objects.filter(
        doctor_id=doctor_id,
        deleted_at__isnull=True,
        status__in=['pending', 'confirmed']  # consider only active appointments
    ).values_list('appointment_date', flat=True).distinct()

    # Generate next 30 days (or a reasonable range)
    today = timezone.now().date()
    available_dates = []
    for i in range(30):
        date = today + timezone.timedelta(days=i)
        # If the date is not in the existing booked dates, and it's not a holiday (optional)
        if date not in existing_dates:
            available_dates.append(date.isoformat())

    return JsonResponse({'dates': available_dates})


# ---------- AJAX: Available Time Slots ----------
def get_available_slots_ajax(request):
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    if not doctor_id or not date_str:
        return JsonResponse({'slots': []})

    try:
        date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'slots': []})

    # Generate time slots from 09:00 to 17:00 (step 30 min)
    start_time = timezone.datetime.strptime('09:00', '%H:%M').time()
    end_time = timezone.datetime.strptime('17:00', '%H:%M').time()
    slots = []
    current = timezone.datetime.combine(timezone.now().date(), start_time)
    end = timezone.datetime.combine(timezone.now().date(), end_time)
    while current <= end:
        slots.append(current.strftime('%H:%M'))
        current += timezone.timedelta(minutes=30)

    # Get booked slots for this doctor and date
    booked_times = Appointment.objects.filter(
        doctor_id=doctor_id,
        appointment_date=date,
        deleted_at__isnull=True,
        status__in=['pending', 'confirmed']
    ).values_list('appointment_time', flat=True)

    # Convert booked times to strings for comparison
    booked_str = [t.strftime('%H:%M') for t in booked_times]

    # Filter available slots
    available_slots = [slot for slot in slots if slot not in booked_str]

    return JsonResponse({'slots': available_slots})