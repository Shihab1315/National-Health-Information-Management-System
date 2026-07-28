from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from typing import cast, Optional, List
import logging

    
import base64
from io import BytesIO
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
    
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
from django.http import HttpResponse
from django.utils import timezone

from .models import MedicalRecord, Allergy, ChronicDisease, PastHistory, Vaccination, Attachment, FollowUp
from .forms import MedicalRecordForm, AllergyForm, ChronicDiseaseForm, PastHistoryForm, VaccinationForm, FollowUpForm, AttachmentForm
from .services import get_dashboard_stats, get_recent_records, generate_patient_timeline, get_patient_health_summary
from accounts.decorators import role_required
from patients.models import Patient

logger = logging.getLogger(__name__)


# ======================== DASHBOARD ========================
@login_required
@role_required(['super_admin', 'hospital_admin', 'doctor'])
def dashboard(request):
    """
    Render the medical records dashboard with statistics and recent records.
    """
    stats = get_dashboard_stats()
    recent = get_recent_records(5)
    context = {
        'stats': stats,
        'recent': recent,
    }
    return render(request, 'medical_records/dashboard.html', context)


# ======================== MEDICAL RECORD CRUD ========================
class RecordListView(LoginRequiredMixin, ListView):
    """
    List all medical records with search, filter, and pagination.
    """
    model = MedicalRecord
    template_name = 'medical_records/record_list.html'
    context_object_name = 'records'
    paginate_by = 10
    ordering = ['-visit_date']

    def get_queryset(self):
        qs = MedicalRecord.objects.filter(is_deleted=False).select_related(
            'patient', 'doctor', 'hospital',
            'patient__user', 'doctor__user'
        ).order_by(*self.ordering)

        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(patient__full_name__icontains=search) |
                Q(diagnosis__icontains=search) |
                Q(doctor__full_name__icontains=search) |
                Q(chief_complaint__icontains=search)
            )

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        date_from_str = self.request.GET.get('date_from')
        date_to_str = self.request.GET.get('date_to')
        if date_from_str:
            date_from = parse_date(date_from_str)
            if date_from:
                qs = qs.filter(visit_date__date__gte=date_from)
        if date_to_str:
            date_to = parse_date(date_to_str)
            if date_to:
                qs = qs.filter(visit_date__date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = MedicalRecord.STATUS_CHOICES
        context['search'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class RecordCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new medical record with optional attachments.
    """
    model = MedicalRecord
    form_class = MedicalRecordForm
    template_name = 'medical_records/record_create.html'
    success_url = reverse_lazy('medical_records:record_list')

    def form_valid(self, form):
        """
        Save the record and any uploaded attachments atomically.
        """
        try:
            with transaction.atomic():
                form.instance.created_by = self.request.user
                record = form.save()

                files = self.request.FILES.getlist('attachments')
                for f in files:
                    Attachment.objects.create(
                        medical_record=record,
                        file=f,
                        description=f.name or 'Uploaded file',
                        uploaded_by=self.request.user
                    )

            # ★ FIX: Set self.object so get_success_url works
            self.object = record

            messages.success(self.request, 'Medical record created successfully.')
            return redirect(self.get_success_url())

        except Exception as e:
            logger.error(f"Error creating medical record: {e}", exc_info=True)
            messages.error(self.request, 'An error occurred while creating the record. Please try again.')
            return self.form_invalid(form)


class RecordDetailView(LoginRequiredMixin, DetailView):
    """
    Display a single medical record with its related data.
    """
    model = MedicalRecord
    template_name = 'medical_records/record_detail.html'
    context_object_name = 'record'

    def get_queryset(self):
        return MedicalRecord.objects.select_related(
            'patient', 'doctor', 'hospital',
            'patient__user', 'doctor__user'
        ).prefetch_related('attachments', 'follow_ups')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        record = cast(MedicalRecord, self.get_object())
        patient = record.patient

        context['allergies'] = Allergy.objects.filter(patient=patient).order_by('-recorded_at')
        context['chronic_diseases'] = ChronicDisease.objects.filter(patient=patient, is_active=True).order_by('-diagnosed_date')
        context['past_history'] = PastHistory.objects.filter(patient=patient).first()
        context['vaccinations'] = Vaccination.objects.filter(patient=patient).order_by('-administration_date')[:5]
        context['follow_ups'] = FollowUp.objects.filter(medical_record=record).order_by('scheduled_date')
        context['attachments'] = Attachment.objects.filter(medical_record=record).order_by('-uploaded_at')

        return context


class RecordUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing medical record and optionally add attachments.
    """
    model = MedicalRecord
    form_class = MedicalRecordForm
    template_name = 'medical_records/record_edit.html'
    success_url = reverse_lazy('medical_records:record_list')

    def get_queryset(self):
        return MedicalRecord.objects.select_related('patient', 'doctor')

    def form_valid(self, form):
        """
        Save the record and any new attachments atomically.
        """
        try:
            with transaction.atomic():
                record = form.save()

                files = self.request.FILES.getlist('attachments')
                for f in files:
                    Attachment.objects.create(
                        medical_record=record,
                        file=f,
                        description=f.name or 'Uploaded file',
                        uploaded_by=self.request.user
                    )

            # ★ FIX: Set self.object for consistency
            self.object = record

            messages.success(self.request, 'Medical record updated successfully.')
            return redirect(self.get_success_url())

        except Exception as e:
            logger.error(f"Error updating medical record: {e}", exc_info=True)
            messages.error(self.request, 'An error occurred while updating the record. Please try again.')
            return self.form_invalid(form)


class RecordDeleteView(LoginRequiredMixin, DeleteView):
    """
    Soft delete a medical record (set is_deleted=True).
    """
    model = MedicalRecord
    template_name = 'medical_records/record_delete.html'
    success_url = reverse_lazy('medical_records:record_list')

    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            record = cast(MedicalRecord, self.object)
            record.is_deleted = True
            record.save(update_fields=['is_deleted'])
            messages.success(request, 'Medical record deleted successfully.')
        except Exception as e:
            logger.error(f"Error deleting medical record: {e}", exc_info=True)
            messages.error(request, 'An error occurred while deleting the record.')
        return redirect(self.get_success_url())


# ======================== PATIENT TIMELINE ========================
@login_required
@role_required(['super_admin', 'hospital_admin', 'doctor'])
def patient_timeline(request, patient_id):
    """
    Display a timeline view of a patient's medical history.
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    timeline = generate_patient_timeline(patient)
    summary = get_patient_health_summary(patient)
    context = {
        'patient': patient,
        'timeline': timeline,
        'summary': summary,
    }
    return render(request, 'medical_records/timeline.html', context)


# ======================== ATTACHMENTS ========================
@login_required
@role_required(['super_admin', 'hospital_admin', 'doctor'])
def attachment_upload(request, record_id):
    """
    Upload one or more attachments for a specific medical record via AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    record = get_object_or_404(MedicalRecord, pk=record_id, is_deleted=False)
    files = request.FILES.getlist('files')

    if not files:
        return JsonResponse({'status': 'error', 'message': 'No files uploaded.'}, status=400)

    uploaded = []
    errors = []

    for f in files:
        try:
            att = Attachment(
                medical_record=record,
                file=f,
                description=f.name,
                uploaded_by=request.user
            )
            att.full_clean()
            att.save()
            uploaded.append(f.name)
        except ValidationError as e:
            errors.append(f"{f.name}: {', '.join(e.messages)}")
        except Exception as e:
            logger.error(f"Attachment upload error for {f.name}: {e}", exc_info=True)
            errors.append(f"{f.name}: Upload failed.")

    if errors:
        return JsonResponse({
            'status': 'partial',
            'uploaded': uploaded,
            'errors': errors,
            'message': 'Some files were not uploaded.'
        }, status=207)

    return JsonResponse({'status': 'success', 'uploaded': uploaded})


@login_required
@role_required(['super_admin', 'hospital_admin', 'doctor'])
def attachment_list(request, pk):
    """
    List all attachments for a specific medical record.
    """
    record = get_object_or_404(MedicalRecord, pk=pk, is_deleted=False)
    attachments = Attachment.objects.filter(medical_record=record).select_related('uploaded_by').order_by('-uploaded_at')
    context = {
        'record': record,
        'attachments': attachments,
    }
    return render(request, 'medical_records/attachments.html', context)




@login_required
@role_required(['patient'])
def patient_medical_record_list(request):
    """
    Patient-specific medical record list.
    Shows only the logged-in patient's own medical records.
    """
    patient = request.user.patient_profile

    # Base queryset – only this patient's records, not soft-deleted
    base_qs = MedicalRecord.objects.filter(
        patient=patient,
        is_deleted=False   # ✅ correct soft-delete field
    ).select_related(
        'doctor',
        'hospital'
    ).order_by('-visit_date')

    # ---------- Statistics ----------
    total = base_qs.count()
    total_hospitals = base_qs.values('hospital').distinct().count()
    total_doctors = base_qs.values('doctor').distinct().count()

    # ---------- Search ----------
    search = request.GET.get('search', '')
    if search:
        base_qs = base_qs.filter(
            Q(diagnosis__icontains=search) |
            Q(doctor__full_name__icontains=search) |
            Q(hospital__name__icontains=search) |
            Q(chief_complaint__icontains=search) |
            Q(clinical_findings__icontains=search)
        ).distinct()

    # ---------- Filters ----------
    hospital_filter = request.GET.get('hospital', '')
    if hospital_filter:
        base_qs = base_qs.filter(hospital_id=hospital_filter)

    doctor_filter = request.GET.get('doctor', '')
    if doctor_filter:
        base_qs = base_qs.filter(doctor_id=doctor_filter)

    diagnosis_filter = request.GET.get('diagnosis', '')
    if diagnosis_filter:
        base_qs = base_qs.filter(diagnosis__icontains=diagnosis_filter)

    # Status filter (if the field exists)
    if hasattr(MedicalRecord, 'status'):
        status_filter = request.GET.get('status', '')
        if status_filter:
            base_qs = base_qs.filter(status=status_filter)

    # ---------- Date range ----------
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        base_qs = base_qs.filter(visit_date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(visit_date__lte=date_to)

    # ---------- Period shortcuts ----------
    period = request.GET.get('period', '')
    today = timezone.now().date()
    if period == 'today':
        base_qs = base_qs.filter(visit_date=today)
    elif period == 'month':
        month_ago = today - timezone.timedelta(days=30)
        base_qs = base_qs.filter(visit_date__gte=month_ago)
    elif period == 'six_months':
        six_months_ago = today - timezone.timedelta(days=180)
        base_qs = base_qs.filter(visit_date__gte=six_months_ago)
    elif period == 'year':
        year_ago = today - timezone.timedelta(days=365)
        base_qs = base_qs.filter(visit_date__gte=year_ago)

    # ---------- Sorting ----------
    sort = request.GET.get('sort', '-visit_date')
    allowed_sort = ['visit_date', '-visit_date', 'doctor__full_name', 'hospital__name']
    if sort in allowed_sort:
        base_qs = base_qs.order_by(sort)
    else:
        base_qs = base_qs.order_by('-visit_date')

    # ---------- Pagination ----------
    paginator = Paginator(base_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ---------- Context for filters ----------
    from hospitals.models import Hospital
    from doctors.models import Doctor

    hospitals = Hospital.objects.filter(is_deleted=False)
    doctors = Doctor.objects.filter(is_active=True)

    # Status choices (if the model has a status field)
    status_choices = []
    if hasattr(MedicalRecord, 'STATUS_CHOICES'):
        status_choices = MedicalRecord.STATUS_CHOICES
    elif hasattr(MedicalRecord, 'status') and hasattr(MedicalRecord._meta.get_field('status'), 'choices'):
        status_choices = MedicalRecord._meta.get_field('status').choices

    context = {
        'page_obj': page_obj,
        'records': page_obj,
        'total': total,
        'total_hospitals': total_hospitals,
        'total_doctors': total_doctors,
        'search': search,
        'hospital_filter': hospital_filter,
        'doctor_filter': doctor_filter,
        'diagnosis_filter': diagnosis_filter,
        'date_from': date_from,
        'date_to': date_to,
        'period': period,
        'sort': sort,
        'hospitals': hospitals,
        'doctors': doctors,
        'status_choices': status_choices,
        'patient': patient,
        'current_date': timezone.now(),
    }
    return render(request, 'medical_records/patient/medical_record_list.html', context)

@login_required
@role_required(['patient'])
def patient_medical_record_detail(request, pk):
    """
    Patient-specific medical record detail view.
    Only the patient who owns the record can view it.
    """
    # Fetch the record with all related data
    record = get_object_or_404(
        MedicalRecord.objects.select_related(
            'patient',
            'doctor',
            'hospital',
            'appointment',
            'prescription',
            'lab_order'
        ).prefetch_related(
            'attachments'
        ),
        pk=pk,
        is_deleted=False
    )

    # Security: ensure the logged-in patient owns this record
    patient = request.user.patient_profile
    if record.patient != patient:
        raise PermissionDenied(_("You do not have permission to view this medical record."))

    # Build timeline (based on available dates)
    timeline = []
    # Visit registered (created_at)
    timeline.append({
        'stage': 'Visit Registered',
        'date': record.created_at,
        'icon': 'fa-calendar-plus',
        'color': 'blue'
    })
    # Doctor consultation (visit_date)
    if record.visit_date:
        timeline.append({
            'stage': 'Doctor Consultation',
            'date': record.visit_date,
            'icon': 'fa-user-md',
            'color': 'emerald'
        })
    # Diagnosis (if diagnosis exists)
    if record.diagnosis:
        timeline.append({
            'stage': 'Diagnosis',
            'date': record.visit_date,  # same day
            'icon': 'fa-stethoscope',
            'color': 'purple'
        })
    # Prescription (if exists)
    if record.prescription:
        timeline.append({
            'stage': 'Prescription Issued',
            'date': record.prescription.created_at,
            'icon': 'fa-prescription-bottle',
            'color': 'amber'
        })
    # Laboratory (if exists)
    if record.lab_order:
        timeline.append({
            'stage': 'Laboratory Ordered',
            'date': record.lab_order.ordered_date,
            'icon': 'fa-flask',
            'color': 'rose'
        })
    # Completed (if status is 'closed' or 'completed')
    if record.status in ['closed', 'completed']:
        timeline.append({
            'stage': 'Visit Completed',
            'date': record.updated_at,
            'icon': 'fa-check-circle',
            'color': 'green'
        })

    # Determine status display
    status_display = record.get_status_display() if hasattr(record, 'get_status_display') else record.status

    context = {
        'record': record,
        'patient': patient,
        'status_display': status_display,
        'timeline': timeline,
        'current_date': timezone.now(),
    }
    return render(request, 'medical_records/patient/medical_record_detail.html', context)


def generate_medical_record_pdf(record):
    """
    Generate a professional medical record PDF using ReportLab.
    Reuses the same pattern as Appointment Slip, Prescription, and Lab Report PDFs.
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
    patient = record.patient
    doctor = record.doctor
    hospital = record.hospital

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

    story.append(Paragraph("MEDICAL RECORD", title_style))
    story.append(Spacer(1, 0.15*inch))

    # ---------- RECORD INFO TABLE ----------
    status_display = record.get_status_display() if hasattr(record, 'get_status_display') else record.status
    data = [
        ["Record Number", str(record.id)],
        ["Visit Date", record.visit_date.strftime("%B %d, %Y") if record.visit_date else "N/A"],
        ["Status", status_display or "N/A"],
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
        ["Emergency Contact", f"{patient.emergency_contact_name or 'N/A'} ({patient.emergency_contact_phone or 'N/A'})"],
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

    doctor_specialties = ', '.join([spec.name for spec in doctor.specialties.all()]) if doctor else "N/A"
    doctor_data = [
        ["Doctor Information", ""],
        ["Name", f"Dr. {doctor.full_name}" if doctor else "N/A"],
        ["Specialization", doctor_specialties],
        ["Qualification", doctor.qualification if doctor else "N/A"],
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

    # ---------- VISIT INFORMATION ----------
    visit_data = [
        ["Visit Date", record.visit_date.strftime("%B %d, %Y") if record.visit_date else "N/A"],
        ["Chief Complaint", record.chief_complaint or "N/A"],
        ["Symptoms", record.symptoms or "N/A"],
    ]
    visit_table = Table(visit_data, colWidths=[3*cm, 8*cm])
    visit_table.setStyle(TableStyle([
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
    story.append(visit_table)
    story.append(Spacer(1, 0.2*inch))

    # ---------- DIAGNOSIS ----------
    story.append(Paragraph("Diagnosis", heading_style))
    story.append(Paragraph(f"<b>Primary Diagnosis:</b> {record.diagnosis or 'N/A'}", normal_style))
    story.append(Paragraph(f"<b>Clinical Findings:</b> {record.clinical_findings or 'N/A'}", normal_style))
    story.append(Spacer(1, 0.15*inch))

    # ---------- VITAL SIGNS ----------
    story.append(Paragraph("Vital Signs", heading_style))
    vital_data = [
        ["Height", f"{record.height or 'N/A'} cm"],
        ["Weight", f"{record.weight or 'N/A'} kg"],
        ["BMI", record.bmi or "N/A"],
        ["Blood Pressure", f"{record.blood_pressure_systolic or 'N/A'}/{record.blood_pressure_diastolic or 'N/A'} mmHg"],
        ["Pulse", f"{record.pulse or 'N/A'} bpm"],
        ["Respiratory Rate", f"{record.respiratory_rate or 'N/A'} /min"],
        ["Temperature", f"{record.temperature or 'N/A'} °F"],
        ["Oxygen Saturation", f"{record.oxygen_saturation or 'N/A'} %"],
    ]
    vital_table = Table(vital_data, colWidths=[3.5*cm, 8*cm])
    vital_table.setStyle(TableStyle([
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
    story.append(vital_table)
    story.append(Spacer(1, 0.2*inch))

    # ---------- DOCTOR NOTES ----------
    story.append(Paragraph("Doctor Notes", heading_style))
    story.append(Paragraph(f"<b>Consultation Notes:</b> {record.doctor_notes or 'N/A'}", normal_style))
    story.append(Paragraph(f"<b>Treatment Plan:</b> {record.treatment_plan or 'N/A'}", normal_style))
    story.append(Spacer(1, 0.15*inch))

    # ---------- MEDICATIONS (if prescription exists) ----------
    if record.prescription:
        story.append(Paragraph("Medications", heading_style))
        medicines = record.prescription.medicines.all()
        if medicines:
            med_data = [["Medicine", "Dosage", "Frequency", "Duration", "Instructions"]]
            for item in medicines:
                med_data.append([
                    item.medicine_name,
                    item.dosage or "—",
                    item.frequency or "—",
                    item.duration or "—",
                    item.instruction or "—",
                ])
            med_table = Table(med_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 2*cm, 3.5*cm])
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
        else:
            story.append(Paragraph("No medications prescribed.", normal_style))
        story.append(Spacer(1, 0.2*inch))

    # ---------- LABORATORY ----------
    if record.lab_order:
        story.append(Paragraph("Laboratory", heading_style))
        story.append(Paragraph(f"Order #: {record.lab_order.order_number}", normal_style))
        story.append(Paragraph(f"Status: {record.lab_order.get_status_display() if hasattr(record.lab_order, 'get_status_display') else record.lab_order.status}", normal_style))
        # List tests (if any)
        if hasattr(record.lab_order, 'items'):
            items = record.lab_order.items.all()
            if items:
                lab_data = [["Test", "Status"]]
                for item in items:
                    lab_data.append([
                        item.test.name if item.test else "N/A",
                        item.status if hasattr(item, 'status') else "N/A",
                    ])
                lab_table = Table(lab_data, colWidths=[6*cm, 4*cm])
                lab_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                story.append(lab_table)
        story.append(Spacer(1, 0.15*inch))

    # ---------- PRESCRIPTIONS ----------
    if record.prescription:
        story.append(Paragraph("Prescription", heading_style))
        story.append(Paragraph(f"Prescription Number: {record.prescription.prescription_number}", normal_style))
        story.append(Paragraph(f"Date: {record.prescription.created_at.strftime('%B %d, %Y')}", normal_style))
        story.append(Paragraph(f"Status: {record.prescription.get_status_display() if hasattr(record.prescription, 'get_status_display') else record.prescription.status}", normal_style))
        story.append(Spacer(1, 0.1*inch))

    # ---------- ATTACHMENTS ----------
    attachments = record.attachments.all() if hasattr(record, 'attachments') else []
    if attachments:
        story.append(Paragraph("Attachments", heading_style))
        for att in attachments:
            story.append(Paragraph(f"• {att.file.name}", normal_style))
        story.append(Spacer(1, 0.15*inch))

    # ---------- QR CODE ----------
    qr_data = f"NHIMS:MR:{record.id}:{patient.id}"
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
    <b>Hospital Seal</b><br/>
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

    footer_text = f"""
    Generated by NHIMS • {timezone.now().strftime("%B %d, %Y %H:%M")} • Medical Record #{record.id}
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
def download_medical_record_pdf(request, pk):
    """
    Download a medical record as a professional PDF.
    Only the patient who owns the record can download.
    """
    record = get_object_or_404(
        MedicalRecord.objects.select_related(
            'patient',
            'doctor',
            'hospital',
            'prescription',
            'lab_order'
        ).prefetch_related(
            'attachments'
        ),
        pk=pk,
        is_deleted=False
    )

    patient = request.user.patient_profile
    if record.patient != patient:
        raise PermissionDenied(_("You do not have permission to download this medical record."))

    pdf_buffer = generate_medical_record_pdf(record)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"medical_record_{record.id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response




    
    
@login_required
@role_required(['patient'])
def print_medical_record(request, pk):
    """
    Print‑optimized view that automatically triggers the browser print dialog.
    Only the patient who owns the record can print it.
    """
    record = get_object_or_404(
        MedicalRecord.objects.select_related(
            'patient',
            'doctor',
            'hospital',
            'prescription',
            'lab_order'
        ).prefetch_related(
            'attachments'
        ),
        pk=pk,
        is_deleted=False
    )

    patient = request.user.patient_profile
    if record.patient != patient:
        raise PermissionDenied(_("You do not have permission to print this medical record."))

    # Generate QR code as base64 for the HTML page
    qr_data = f"NHIMS:MR:{record.id}:{patient.id}"
    qr_img = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{qr_base64}"

    # Determine status display
    get_status_display_method = getattr(record, 'get_status_display', None)
    status_display = (
        get_status_display_method()
        if callable(get_status_display_method)
        else record.status
    )

    context = {
        'record': record,
        'patient': patient,
        'status_display': status_display,
        'qr_image_data': qr_image_data,
        'current_date': timezone.now(),
        'auto_print': True,
    }
    return render(request, 'medical_records/patient/medical_record_print.html', context)
