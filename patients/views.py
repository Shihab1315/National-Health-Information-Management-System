from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Patient,PatientSettings  # MedicalRecord আর নেই
from .forms import PatientForm, PatientSettingsForm
from accounts.decorators import role_required
from django.contrib.auth import logout

from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from accounts.decorators import role_required
from appointments.models import Appointment
from prescriptions.models import Prescription
from laboratory.models import LabResult
from medical_records.models import MedicalRecord
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.decorators import role_required
from django.utils.decorators import method_decorator
import base64
from io import BytesIO

import io
import qrcode
import barcode
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import A4, mm, inch
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.utils import ImageReader
from django.http import HttpResponse




@login_required
@role_required(['super_admin','hospital_admin','doctor','receptionist'])
def patient_list(request):
    patients = Patient.objects.all()

    # Search
    search_query = request.GET.get('q')
    if search_query:
        patients = patients.filter(
            Q(full_name__icontains=search_query) |
            Q(health_id__icontains=search_query) |
            Q(national_id__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(district__icontains=search_query)
        )

    # Filter by district
    district_filter = request.GET.get('district')
    if district_filter:
        patients = patients.filter(district=district_filter)

    # Pagination
    paginator = Paginator(patients, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'district_filter': district_filter,
        
        'districts': Patient.objects.values_list('district', flat=True).distinct().order_by('district'),
    }
    return render(request, 'patients/patient_list.html', context)

@login_required
@role_required(['super_admin','hospital_admin','doctor','receptionist'])
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    records = patient.medical_records.all()

    return render(request, "patients/patient_detail.html", {
        "patient": patient,
        "records": records,
    })

@login_required
@role_required(['super_admin','hospital_admin','doctor','receptionist'])
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Patient {patient.full_name} created successfully!')
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = PatientForm()
    return render(request, 'patients/patient_form.html', {'form': form, 'title': 'Add New Patient'})

@login_required
@role_required(['super_admin','hospital_admin','doctor','receptionist'])
def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient {patient.full_name} updated successfully!')
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/patient_form.html', {'form': form, 'title': 'Edit Patient', 'patient': patient})

@login_required
@role_required(['super_admin','hospital_admin','doctor','receptionist'])
def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        messages.success(request, 'Patient deleted successfully.')
        return redirect('patients:list')
    return render(request, 'patients/patient_confirm_delete.html', {'patient': patient})

@login_required
@role_required(['patient'])
def patient_profile(request):
    """
    Patient profile view – displays complete patient information,
    statistics, and recent activities.
    """
    patient = request.user.patient_profile

    # ---------- Statistics ----------
    total_appointments = Appointment.objects.filter(patient=patient, deleted_at__isnull=True).count()
    total_prescriptions = Prescription.objects.filter(patient=patient, deleted_at__isnull=True).count()
    total_lab_reports = LabResult.objects.filter(
        order_item__lab_order__patient=patient,
        deleted_at__isnull=True
    ).count()
    total_medical_records = MedicalRecord.objects.filter(patient=patient, is_deleted=False).count()

    # ---------- Recent Activities ----------
    # Last appointment
    last_appointment = Appointment.objects.filter(
        patient=patient,
        deleted_at__isnull=True
    ).order_by('-appointment_date').first()

    # Last prescription
    last_prescription = Prescription.objects.filter(
        patient=patient,
        deleted_at__isnull=True
    ).order_by('-created_at').first()

    # Last lab report
    last_lab_report = LabResult.objects.filter(
        order_item__lab_order__patient=patient,
        deleted_at__isnull=True
    ).order_by('-created_at').first()

    # Last login (from user)
    last_login = request.user.last_login

    # ---------- Primary Doctor (from most recent appointment) ----------
    primary_doctor = None
    latest_appointment = Appointment.objects.filter(
        patient=patient,
        deleted_at__isnull=True,
        doctor__isnull=False
    ).select_related('doctor').order_by('-appointment_date').first()
    if latest_appointment and latest_appointment.doctor:
        primary_doctor = latest_appointment.doctor

    # ---------- Insurance (if exists) ----------
    insurance = getattr(patient, 'insurance', None)  # if the model has an insurance related field

    # ---------- Profile Completion ----------
    # Calculate percentage of filled fields
    fields_to_check = [
        patient.full_name,
        patient.date_of_birth,
        patient.gender,
        patient.blood_group,
        patient.phone,
        patient.email,
        patient.address,
        patient.emergency_contact_name,
        patient.emergency_contact_phone,
    ]
    filled_fields = sum(1 for field in fields_to_check if field and field != 'Unknown')
    total_fields = len(fields_to_check)
    completion_percent = int((filled_fields / total_fields) * 100) if total_fields > 0 else 0

    # ---------- Context ----------
    context = {
        'patient': patient,
        'total_appointments': total_appointments,
        'total_prescriptions': total_prescriptions,
        'total_lab_reports': total_lab_reports,
        'total_medical_records': total_medical_records,
        'last_appointment': last_appointment,
        'last_prescription': last_prescription,
        'last_lab_report': last_lab_report,
        'last_login': last_login,
        'primary_doctor': primary_doctor,
        'insurance': insurance,
        'completion_percent': completion_percent,
        'current_date': timezone.now(),
    }
    return render(request, 'patients/patient_profile.html', context)

@login_required
@role_required(['patient'])
def edit_patient_profile(request):
    """
    Edit patient profile view.
    Only the logged-in patient can edit his own profile.
    """
    patient = request.user.patient_profile

    if request.method == 'POST':
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('patients:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientForm(instance=patient)

    context = {
        'form': form,
        'patient': patient,
        'current_date': timezone.now(),
    }
    return render(request, 'patients/edit_profile.html', context)

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(['patient']), name='dispatch')
class ChangePasswordView(PasswordChangeView):
    template_name = 'patients/change_password.html'
    success_url = reverse_lazy('patients:profile')

    def form_valid(self, form):
        # Update session to keep user logged in after password change
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, 'Your password has been changed successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
@login_required
@role_required(['patient'])
def emergency_contact(request):
    """
    Manage emergency contact information.
    """
    patient = request.user.patient_profile

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Emergency contact updated successfully.')
            return redirect('patients:emergency_contact')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientForm(instance=patient)

    context = {
        'form': form,
        'patient': patient,
        'current_date': timezone.now(),
    }
    return render(request, 'patients/emergency_contact.html', context)

@login_required
@role_required(['patient'])
def medical_information(request):
    """
    Manage permanent medical information for the patient.
    """
    patient = request.user.patient_profile

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medical information updated successfully.')
            return redirect('patients:medical_information')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientForm(instance=patient)

    context = {
        'form': form,
        'patient': patient,
        'current_date': timezone.now(),
    }
    return render(request, 'patients/medical_information.html', context)

@login_required
@role_required(['patient'])
def insurance_information(request):
    patient = request.user.patient_profile

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insurance information updated successfully.')
            return redirect('patients:insurance_information')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientForm(instance=patient)

    # Calculate days remaining for expiry
    days_remaining = None
    if patient.coverage_end_date:
        from datetime import date
        delta = patient.coverage_end_date - date.today()
        days_remaining = delta.days

    context = {
        'form': form,
        'patient': patient,
        'days_remaining': days_remaining,
        'current_date': timezone.now(),
    }
    return render(request, 'patients/insurance_information.html', context)

@login_required
@role_required(['patient'])
def download_patient_card(request):
    """
    Generate and download a professional Patient ID Card PDF.
    Only the logged-in patient can download his own card.
    """
    patient = request.user.patient_profile

    # Generate QR code data
    qr_data = f"NHIMS:PATIENT:{patient.health_id}:{patient.id}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Generate barcode for patient ID (Code128)
    barcode_class = barcode.get_barcode_class('code128')
    barcode_obj = barcode_class(patient.health_id or str(patient.id), writer=ImageWriter())
    barcode_buffer = io.BytesIO()
    barcode_obj.write(barcode_buffer, options={'write_text': False})
    barcode_buffer.seek(0)

    # Create PDF
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
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    normal_style = styles['Normal']
    normal_style.fontName = 'Helvetica'
    normal_style.fontSize = 9
    normal_style.leading = 12

    story = []

    # ---------- HEADER ----------
    from hospitals.models import Hospital
    hospital = Hospital.objects.filter(is_deleted=False).first()
    hospital_name = hospital.name if hospital else "NHIMS Hospital"
    hospital_address = hospital.full_address if hospital and hasattr(hospital, 'full_address') else "Dhaka, Bangladesh"
    hospital_phone = hospital.phone if hospital else "+880 1234 567890"

    header_text = f"""
    <b>{hospital_name}</b><br/>
    {hospital_address}<br/>
    Phone: {hospital_phone}
    """
    story.append(Paragraph(header_text, title_style))
    story.append(Paragraph("National Health Information Management System (NHIMS)", subtitle_style))
    story.append(Paragraph("Government of Bangladesh", subtitle_style))
    story.append(Spacer(1, 0.2*inch))

    # ---------- CARD DESIGN (centered on page) ----------
    # We'll create a card layout using a table with background color
    card_width = 16*cm
    card_height = 9*cm

    # Patient photo / avatar
    if patient.profile_photo and hasattr(patient.profile_photo, 'url'):
        try:
            from django.core.files.storage import default_storage
            from reportlab.lib.utils import ImageReader
            photo_path = patient.profile_photo.path
            photo_img = ImageReader(photo_path)
            photo = Image(photo_img, width=3*cm, height=3*cm)
        except:
            # Fallback to avatar
            photo = Paragraph("No Photo", normal_style)
    else:
        # Create a circle with initials using a Paragraph? We'll just use a placeholder text.
        initials = patient.full_name[:2].upper() if patient.full_name else "P"
        photo = Paragraph(f"<font size=20><b>{initials}</b></font>", ParagraphStyle(
            'AvatarStyle',
            parent=normal_style,
            alignment=TA_CENTER,
            fontSize=20,
            textColor=colors.white,
        ))

    # Patient info (right side)
    info_data = [
        ["Patient ID", patient.health_id or "N/A"],
        ["Name", patient.full_name],
        ["Gender", patient.get_gender_display() or "N/A"],
        ["Date of Birth", patient.date_of_birth.strftime("%d %b %Y") if patient.date_of_birth else "N/A"],
        ["Blood Group", patient.blood_group or "N/A"],
        ["Phone", patient.phone or "N/A"],
        ["Email", patient.email or "N/A"],
    ]

    # Build info table (two columns: label and value)
    info_table_data = []
    for label, value in info_data:
        info_table_data.append([Paragraph(f"<b>{label}</b>", normal_style), Paragraph(value, normal_style)])

    info_table = Table(info_table_data, colWidths=[3*cm, 4.5*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEADING', (0, 0), (-1, -1), 10),
    ]))

    # QR and Barcode (bottom of card)
    qr_image = Image(qr_buffer, width=2*cm, height=2*cm)
    barcode_image = Image(barcode_buffer, width=4*cm, height=1.2*cm)

    # Create card table: left: photo, right: info, bottom: qr+barcode
    card_data = [
        [photo, info_table],
        [qr_image, barcode_image],
    ]
    card_table = Table(card_data, colWidths=[5*cm, 8*cm])
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('ROUNDEDCORNERS', (0, 0), (-1, -1), 5),
    ]))

    # Center the card on the page
    story.append(Spacer(1, 0.5*inch))
    story.append(card_table)
    story.append(Spacer(1, 0.2*inch))

    # ---------- EMERGENCY & MEDICAL INFO ----------
    emergency_text = f"""
    <b>Emergency Contact:</b> {patient.emergency_contact_name or 'N/A'} ({patient.emergency_contact_phone or 'N/A'})
    <br/>
    <b>Allergies:</b> {patient.allergies or 'None'}
    <br/>
    <b>Chronic Diseases:</b> {patient.chronic_diseases or 'None'}
    """
    story.append(Paragraph(emergency_text, normal_style))
    story.append(Spacer(1, 0.1*inch))

    # ---------- INSURANCE ----------
    if patient.has_insurance:
        insurance_text = f"""
        <b>Insurance:</b> {patient.insurance_provider or 'N/A'} | Policy: {patient.policy_number or 'N/A'}
        <br/>
        <b>Coverage:</b> {patient.coverage_amount or 'N/A'} BDT | Expires: {patient.coverage_end_date.strftime('%d %b %Y') if patient.coverage_end_date else 'N/A'}
        """
    else:
        insurance_text = "<b>Insurance:</b> Not Available"
    story.append(Paragraph(insurance_text, normal_style))
    story.append(Spacer(1, 0.1*inch))

    # ---------- FOOTER ----------
    footer_text = f"""
    <i>This card is generated electronically by NHIMS.</i><br/>
    <b>Issue Date:</b> {timezone.now().strftime("%d %b %Y %H:%M")}
    <br/>
    <i>Hospital Contact: {hospital_phone} | This card is for identification purposes only.</i>
    """
    story.append(Paragraph(footer_text, ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey,
    )))

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f"Patient_Card_{patient.health_id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@role_required(['patient'])
def print_patient_card(request):
    """
    Print-optimized view that displays the Patient Card and auto‑triggers print.
    """
    patient = request.user.patient_profile

    # Generate QR code as base64 for HTML
    qr_data = f"NHIMS:PATIENT:{patient.health_id}:{patient.id}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode('utf-8')
    qr_image_data = f"data:image/png;base64,{qr_base64}"

    # Get hospital info
    from hospitals.models import Hospital
    hospital = Hospital.objects.filter(is_deleted=False).first()
    hospital_name = hospital.name if hospital else "NHIMS Hospital"

    context = {
        'patient': patient,
        'qr_image_data': qr_image_data,
        'hospital_name': hospital_name,
        'current_date': timezone.now(),
        'auto_print': True,   # flag to auto‑trigger print
    }
    return render(request, 'patients/patient_card_print.html', context)

@login_required
@role_required(['patient'])
def profile_completion_dashboard(request):
    """
    Profile Completion Dashboard – helps patients understand which profile
    sections are complete and which require attention.
    """
    patient = request.user.patient_profile

    # ---------- SECTION COMPLETION ----------
    sections = {}

    # 1. Profile Photo
    sections['profile_photo'] = {
        'label': 'Profile Photo',
        'completed': bool(patient.profile_photo),
        'url': 'patients:edit_profile',
        'icon': 'fa-user-circle'
    }

    # 2. Personal Information
    personal_fields = [
        bool(patient.full_name and patient.full_name != 'Unknown'),
        bool(patient.date_of_birth and patient.date_of_birth != '2000-01-01'),
        bool(patient.gender),
        bool(patient.phone and patient.phone != '0000000000'),
        bool(patient.email),
        bool(patient.address and patient.address != 'Unknown'),
        bool(patient.national_id and patient.national_id != '0000000000'),
        bool(patient.blood_group),
    ]
    personal_completed = sum(personal_fields)
    personal_total = len(personal_fields)
    sections['personal'] = {
        'label': 'Personal Information',
        'completed': personal_completed == personal_total,
        'completed_count': personal_completed,
        'total': personal_total,
        'url': 'patients:edit_profile',
        'icon': 'fa-user'
    }

    # 3. Emergency Contact
    emergency_completed = bool(
        patient.emergency_contact_name and patient.emergency_contact_phone
    )
    sections['emergency'] = {
        'label': 'Emergency Contact',
        'completed': emergency_completed,
        'url': 'patients:emergency_contact',
        'icon': 'fa-phone-alt'
    }

    # 4. Medical Information
    medical_fields = [
        bool(patient.allergies and patient.allergies.strip()),
        bool(patient.chronic_diseases and patient.chronic_diseases.strip()),
        patient.height is not None,
        patient.weight is not None,
        bool(patient.smoking_status),
        bool(patient.alcohol_consumption),
        bool(patient.exercise_frequency),
        bool(patient.diet_preference),
    ]
    medical_completed = sum(medical_fields)
    medical_total = len(medical_fields)
    sections['medical'] = {
        'label': 'Medical Information',
        'completed': medical_completed == medical_total,
        'completed_count': medical_completed,
        'total': medical_total,
        'url': 'patients:medical_information',
        'icon': 'fa-heartbeat'
    }

    # 5. Insurance
    insurance_completed = patient.has_insurance and bool(
        patient.insurance_provider and patient.policy_number
    )
    sections['insurance'] = {
        'label': 'Insurance Information',
        'completed': insurance_completed,
        'url': 'patients:insurance_information',
        'icon': 'fa-shield-alt'
    }

    # ---------- OVERALL COMPLETION ----------
    total_completed = sum(1 for s in sections.values() if s['completed'] is True)
    total_sections = len(sections)
    overall_percent = int((total_completed / total_sections) * 100) if total_sections > 0 else 0

    # Profile strength
    if overall_percent >= 90:
        strength = 'Excellent'
        strength_color = 'text-emerald-400'
        strength_bg = 'bg-emerald-500/20'
    elif overall_percent >= 70:
        strength = 'Good'
        strength_color = 'text-blue-400'
        strength_bg = 'bg-blue-500/20'
    elif overall_percent >= 50:
        strength = 'Average'
        strength_color = 'text-amber-400'
        strength_bg = 'bg-amber-500/20'
    else:
        strength = 'Poor'
        strength_color = 'text-red-400'
        strength_bg = 'bg-red-500/20'

    # ---------- ACHIEVEMENTS ----------
    achievements = []
    if overall_percent == 100:
        achievements.append({'label': 'Profile Completed', 'icon': 'fa-check-circle', 'color': 'emerald'})
    if patient.email:
        achievements.append({'label': 'Email Added', 'icon': 'fa-envelope', 'color': 'blue'})
    if patient.phone and patient.phone != '0000000000':
        achievements.append({'label': 'Phone Verified', 'icon': 'fa-phone', 'color': 'green'})
    if insurance_completed:
        achievements.append({'label': 'Insurance Added', 'icon': 'fa-shield-alt', 'color': 'purple'})
    if emergency_completed:
        achievements.append({'label': 'Emergency Contact Added', 'icon': 'fa-phone-alt', 'color': 'amber'})
    if medical_completed >= 4:
        achievements.append({'label': 'Medical Information Complete', 'icon': 'fa-heartbeat', 'color': 'rose'})

    # ---------- RECOMMENDATIONS ----------
    recommendations = []
    if not patient.profile_photo:
        recommendations.append({'label': 'Upload Profile Photo', 'url': 'patients:edit_profile'})
    if not emergency_completed:
        recommendations.append({'label': 'Complete Emergency Contact', 'url': 'patients:emergency_contact'})
    if not insurance_completed:
        recommendations.append({'label': 'Add Insurance Information', 'url': 'patients:insurance_information'})
    if medical_completed < 4:
        recommendations.append({'label': 'Update Medical Information', 'url': 'patients:medical_information'})
    if personal_completed < 5:
        recommendations.append({'label': 'Complete Personal Information', 'url': 'patients:edit_profile'})

    # ---------- SUMMARY CARDS ----------
    from appointments.models import Appointment
    from prescriptions.models import Prescription
    from laboratory.models import LabResult
    from medical_records.models import MedicalRecord

    total_appointments = Appointment.objects.filter(patient=patient, deleted_at__isnull=True).count()
    total_prescriptions = Prescription.objects.filter(patient=patient, deleted_at__isnull=True).count()
    total_lab_reports = LabResult.objects.filter(
        order_item__lab_order__patient=patient,
        deleted_at__isnull=True
    ).count()
    total_medical_records = MedicalRecord.objects.filter(patient=patient, is_deleted=False).count()

    # ---------- RECENT ACTIVITY (fixed sorting) ----------
    recent_activities = []

    def to_date(value):
        """Convert to date object safely."""
        if hasattr(value, 'date'):
            return value.date()
        return value

    last_appointment = Appointment.objects.filter(patient=patient, deleted_at__isnull=True).order_by('-appointment_date').first()
    if last_appointment:
        recent_activities.append({
            'type': 'Appointment',
            'date': to_date(last_appointment.appointment_date),
            'title': f'Appointment with Dr. {last_appointment.doctor.full_name}',
            'icon': 'fa-calendar-check',
            'color': 'blue'
        })

    last_prescription = Prescription.objects.filter(patient=patient, deleted_at__isnull=True).order_by('-created_at').first()
    if last_prescription:
        recent_activities.append({
            'type': 'Prescription',
            'date': to_date(last_prescription.created_at),
            'title': f'Prescription #{last_prescription.prescription_number}',
            'icon': 'fa-prescription-bottle',
            'color': 'emerald'
        })

    last_lab = LabResult.objects.filter(
        order_item__lab_order__patient=patient,
        deleted_at__isnull=True
    ).order_by('-created_at').first()
    if last_lab:
        recent_activities.append({
            'type': 'Lab Report',
            'date': to_date(last_lab.created_at),
            'title': f'Lab Report for {last_lab.order_item.test.name}',
            'icon': 'fa-flask',
            'color': 'amber'
        })

    last_record = MedicalRecord.objects.filter(patient=patient, is_deleted=False).order_by('-visit_date').first()
    if last_record:
        recent_activities.append({
            'type': 'Medical Record',
            'date': to_date(last_record.visit_date),
            'title': f'Medical Record #{last_record.id}',
            'icon': 'fa-file-medical',
            'color': 'purple'
        })

    # Sort by date (newest first)
    recent_activities.sort(key=lambda x: x['date'], reverse=True)

    # ---------- ACCOUNT STATUS ----------
    if overall_percent == 100:
        account_status = 'Verified'
        status_color = 'text-emerald-400'
    elif overall_percent >= 60:
        account_status = 'Incomplete'
        status_color = 'text-amber-400'
    else:
        account_status = 'Pending'
        status_color = 'text-red-400'

    context = {
        'patient': patient,
        'sections': sections,
        'overall_percent': overall_percent,
        'strength': strength,
        'strength_color': strength_color,
        'strength_bg': strength_bg,
        'achievements': achievements,
        'recommendations': recommendations,
        'total_appointments': total_appointments,
        'total_prescriptions': total_prescriptions,
        'total_lab_reports': total_lab_reports,
        'total_medical_records': total_medical_records,
        'recent_activities': recent_activities,
        'account_status': account_status,
        'status_color': status_color,
        'current_date': timezone.now(),
    }

    return render(request, 'patients/profile_completion_dashboard.html', context)

import logging
logger = logging.getLogger(__name__)

@login_required
@role_required(['patient'])
def patient_settings(request):
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "You are not registered as a patient.")
        return redirect('patient_dashboard')

    settings, created = PatientSettings.objects.get_or_create(patient=patient)

    if request.method == 'POST':
        # Handle special actions
        if 'logout' in request.POST:
            logout(request)
            return redirect('home')
        if 'deactivate' in request.POST:
            user = request.user
            user.is_active = False
            user.save()
            logout(request)
            return redirect('home')
        if 'delete' in request.POST:
            messages.error(request, "Account deletion is not available.")
            return redirect('patients:patient_settings')

        form = PatientSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            # Save the form but don't commit yet
            updated_settings = form.save(commit=False)
            # For all boolean fields, if missing from POST, set to False
            boolean_fields = [
                'notify_appointments', 'notify_prescriptions', 'notify_laboratory', 'notify_system',
                'show_mobile', 'show_email', 'hide_personal_info',
                'large_font', 'high_contrast', 'reduced_motion'
            ]
            for field in boolean_fields:
                if field not in request.POST:
                    setattr(updated_settings, field, False)
            updated_settings.save()
            print("Appearance:", updated_settings.appearance)
            print("Language:", updated_settings.language)
            print("Appointments:", updated_settings.notify_appointments)
            print("Prescription:", updated_settings.notify_prescriptions)
            messages.success(request, "Settings updated successfully.")
            return redirect('patients:patient_settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        if request.GET.get('reset'):
            for field in settings._meta.fields:
                if field.name not in ['id', 'patient', 'updated_at']:
                    setattr(settings, field.name, field.default)
            settings.save()
            messages.success(request, "Settings reset to defaults.")
            return redirect('patients:patient_settings')
        form = PatientSettingsForm(instance=settings)

    return render(request, 'patients/settings.html', {
        'form': form,
        'settings': settings,
        'patient': patient,
        'active_sessions': 1,
    })
    
def logout_view(request):
    """
    Secure logout via POST only.
    Clears session, logs out the user, and redirects to login with a success flag.
    """
    if request.method != 'POST':
        # Only POST allowed – redirect to dashboard or home
        return redirect('patient_dashboard')
    
    logout(request)
    # Redirect to login page with a query parameter to show success message
    return redirect(reverse('accounts:login') + '?logged_out=true')