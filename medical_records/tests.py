import os
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.test import TestCase, Client, override_settings, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import time

from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital
from appointments.models import Appointment
from prescriptions.models import Prescription
from laboratory.models import LabOrder

from medical_records.models import (
    MedicalRecord, Allergy, ChronicDisease, PastHistory,
    Vaccination, Attachment, FollowUp
)
from medical_records.forms import (
    MedicalRecordForm, AllergyForm, ChronicDiseaseForm,
    PastHistoryForm, VaccinationForm, FollowUpForm, AttachmentForm
)
from medical_records.services import (
    get_dashboard_stats, get_recent_records, generate_patient_timeline,
    get_patient_health_summary, get_patient_statistics,
    get_patient_last_record, get_patient_latest_prescription,
    get_patient_latest_lab, get_patient_allergies,
    get_patient_chronic_diseases, get_patient_followups,
    get_recent_followups, get_critical_patients,
    get_doctor_statistics, get_hospital_statistics,
    search_medical_records, get_monthly_statistics,
    get_yearly_statistics, calculate_dashboard_metrics,
    build_patient_summary, build_dashboard_cards
)
from medical_records.utils import (
    calculate_bmi, get_health_summary, generate_health_id,
    get_upcoming_follow_ups, format_blood_pressure,
    get_bmi_category, calculate_age, calculate_bsa,
    validate_vital_signs, calculate_risk_level,
    calculate_followup_days, generate_medical_record_number,
    generate_attachment_path, safe_decimal, safe_percentage,
    format_temperature, format_weight, format_height,
    format_datetime, get_current_age_in_months, is_valid_date_range
)
from medical_records.validators import (
    validate_positive_number, validate_weight, validate_height,
    validate_blood_pressure_systolic, validate_blood_pressure_diastolic,
    validate_pulse, validate_temperature, validate_oxygen_saturation,
    validate_file_extension, validate_file_size,
    validate_bmi, validate_respiratory_rate,
    validate_followup_date, validate_visit_date,
    validate_future_date, validate_not_future_datetime,
    validate_medical_notes, validate_diagnosis,
    validate_chief_complaint, validate_phone_number,
    validate_email, validate_age, validate_dose_number,
    validate_attachment_name, validate_file_name,
    validate_image_extension, validate_document_extension,
    validate_pdf_extension, validate_percentage, validate_text_length
)
from medical_records.signals import (
    auto_calculate_bmi, create_follow_up_reminder,
    notify_followup_reminder, update_patient_timeline_cache,
    update_medical_record_status, log_followup_deletion
)

User = get_user_model()


class MedicalRecordsTestBase(TestCase):
    """Base test class with common setup for all medical records tests."""

    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.user = User.objects.create_user(
            username='doctor1', password='testpass123',
            email='doctor1@example.com', role='doctor'
        )
        cls.admin_user = User.objects.create_user(
            username='admin', password='adminpass123',
            email='admin@example.com', role='super_admin'
        )

        # Create patient
        cls.patient = Patient.objects.create(
            full_name='Test Patient',
            national_id='1234567890',
            date_of_birth='1990-01-01',
            gender='M',
            phone='01712345678',
            address='Dhaka',
            city='Dhaka',
            district='Dhaka'
        )

        # Create hospital
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            registration_number='HOSP123',
            hospital_type='private',
            ownership='private_owned',
            description='Test Hospital Description',
            full_address='Dhaka, Bangladesh',
            country='Bangladesh',
            division='Dhaka',
            district='Dhaka',
            city='Dhaka',
            email='hospital@test.com',
            phone='01912345678'
        )

        # Create doctor with the hospital
        cls.doctor = Doctor.objects.create(
            user=cls.user,
            hospital=cls.hospital,
            full_name='Dr. Test Doctor',
            national_id='0987654321',
            registration_number='REG12345',
            gender='M',
            date_of_birth='1980-01-01',
            phone='01812345678',
            address='Dhaka',
            city='Dhaka',
            district='Dhaka',
            qualification='MBBS'
        )

        # Create appointment
        cls.appointment = Appointment.objects.create(
           hospital=cls.hospital,
           patient=cls.patient,
           doctor=cls.doctor,
           appointment_date=date.today(),
           appointment_time=time(10, 0),   
           appointment_number="APPT-001",
        )

        # Create prescription
        cls.prescription = Prescription.objects.create(
            appointment=cls.appointment,
            hospital=cls.hospital,
            doctor=cls.doctor,
            patient=cls.patient,
            diagnosis='Test Diagnosis',
            status=Prescription.Status.DRAFT,
            prescription_number='RX-001'
        )

        # Create lab order
        cls.lab_order = LabOrder.objects.create(
            prescription=cls.prescription,
            appointment=cls.appointment,
            patient=cls.patient,
            doctor=cls.doctor,
            hospital=cls.hospital,
            status=LabOrder.Status.ORDERED,
            order_number='LAB-001'
        )

        cls.client = Client()


class MedicalRecordModelTests(MedicalRecordsTestBase):
    """Tests for MedicalRecord model."""

    def test_create_medical_record(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital,
            appointment=self.appointment,
            prescription=self.prescription,
            lab_order=self.lab_order,
            visit_date=timezone.now(),
            chief_complaint='Headache',
            symptoms='Pain',
            history_of_present_illness='Started yesterday',
            diagnosis='Migraine',
            clinical_findings='Normal',
            status='active',
            created_by=self.user
        )
        self.assertEqual(record.patient, self.patient)
        self.assertEqual(record.diagnosis, 'Migraine')
        self.assertEqual(record.status, 'active')
        self.assertFalse(record.is_deleted)
        self.assertEqual(str(record), f"Record for {self.patient.full_name} - {record.visit_date.strftime('%Y-%m-%d')}")

    def test_bmi_value_property(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Chest pain',
            diagnosis='Angina',
            height=175.0,
            weight=75.0
        )
        self.assertEqual(record.bmi_value, 24.49)

    def test_bmi_value_with_missing_data(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Chest pain',
            diagnosis='Angina'
        )
        self.assertIsNone(record.bmi_value)

    def test_clean_validation(self):
        record = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            follow_up_date=timezone.now().date() - timedelta(days=1),
            chief_complaint='Headache',
            diagnosis='Migraine'
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

        record = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Headache',
            diagnosis='Migraine',
            blood_pressure_systolic=120,
            blood_pressure_diastolic=130
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

        record = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Headache',
            diagnosis='Migraine',
            pulse=250
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_soft_delete(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        record.is_deleted = True
        record.save()
        self.assertTrue(record.is_deleted)
        qs = MedicalRecord.objects.filter(is_deleted=False)
        self.assertNotIn(record, qs)


class AllergyModelTests(MedicalRecordsTestBase):
    """Tests for Allergy model."""

    def test_create_allergy(self):
        allergy = Allergy.objects.create(
            patient=self.patient,
            allergen='Penicillin',
            severity='severe',
            reaction='Rash',
            notes='Test note'
        )
        self.assertEqual(allergy.patient, self.patient)
        self.assertEqual(allergy.allergen, 'Penicillin')
        self.assertEqual(allergy.severity, 'severe')
        self.assertEqual(str(allergy), f"{self.patient.full_name} - Penicillin")


class ChronicDiseaseModelTests(MedicalRecordsTestBase):
    """Tests for ChronicDisease model."""

    def test_create_chronic_disease(self):
        disease = ChronicDisease.objects.create(
            patient=self.patient,
            disease='diabetes',
            diagnosed_date=date(2020, 1, 1),
            is_active=True
        )
        self.assertEqual(disease.patient, self.patient)
        self.assertEqual(disease.disease, 'diabetes')
        self.assertTrue(disease.is_active)
        self.assertEqual(str(disease), f"{self.patient.full_name} - Diabetes")


class PastHistoryModelTests(MedicalRecordsTestBase):
    """Tests for PastHistory model."""

    def test_create_past_history(self):
        history = PastHistory.objects.create(
            patient=self.patient,
            surgeries='Appendectomy 2015',
            hospital_admissions='Admission 2018',
            family_history='Diabetes',
            smoking_status='never',
            alcohol_consumption='occasional',
            occupation='Engineer'
        )
        self.assertEqual(history.patient, self.patient)
        self.assertEqual(history.smoking_status, 'never')
        self.assertEqual(str(history), f"History for {self.patient.full_name}")


class VaccinationModelTests(MedicalRecordsTestBase):
    """Tests for Vaccination model."""

    def test_create_vaccination(self):
        vaccination = Vaccination.objects.create(
            patient=self.patient,
            vaccine='covid',
            dose_number=1,
            administration_date=date(2021, 1, 1),
            administered_by='Dr. Test'
        )
        self.assertEqual(vaccination.patient, self.patient)
        self.assertEqual(vaccination.vaccine, 'covid')
        self.assertEqual(vaccination.dose_number, 1)
        self.assertEqual(str(vaccination), f"{self.patient.full_name} - COVID-19 (1)")


class AttachmentModelTests(MedicalRecordsTestBase):
    """Tests for Attachment model."""

    def test_create_attachment(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        file = SimpleUploadedFile("test.txt", b"file content", content_type="text/plain")
        attachment = Attachment.objects.create(
            medical_record=record,
            file=file,
            description='Test file',
            uploaded_by=self.user
        )
        self.assertEqual(attachment.medical_record, record)
        self.assertEqual(attachment.description, 'Test file')
        self.assertEqual(str(attachment), f"Attachment for {self.patient.full_name}")


class FollowUpModelTests(MedicalRecordsTestBase):
    """Tests for FollowUp model."""

    def test_create_followup(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        followup = FollowUp.objects.create(
            medical_record=record,
            scheduled_date=timezone.now() + timedelta(days=7),
            status='scheduled',
            notes='Follow-up in 7 days'
        )
        self.assertEqual(followup.medical_record, record)
        self.assertEqual(followup.status, 'scheduled')
        self.assertEqual(str(followup), f"Follow-up for {self.patient.full_name} - {followup.scheduled_date.strftime('%Y-%m-%d')}")


class MedicalRecordFormTests(MedicalRecordsTestBase):
    """Tests for MedicalRecordForm."""

    def test_valid_form(self):
        now = timezone.now()
        form_data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'hospital': self.hospital.id,
            'visit_date': now.strftime('%Y-%m-%dT%H:%M'),
            'chief_complaint': 'Headache',
            'diagnosis': 'Migraine',
            'status': 'active',
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'pulse': 72,
            'temperature': 98.6,
            'height': 175.0,
            'weight': 75.0,
            'oxygen_saturation': 98,
            'respiratory_rate': 16,
        }
        form = MedicalRecordForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_blood_pressure(self):
        now = timezone.now()
        form_data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'visit_date': now.strftime('%Y-%m-%dT%H:%M'),
            'chief_complaint': 'Headache',
            'diagnosis': 'Migraine',
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 130,
        }
        form = MedicalRecordForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('blood_pressure_systolic', form.errors)

    def test_invalid_followup_date(self):
        now = timezone.now()
        form_data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'visit_date': now.strftime('%Y-%m-%dT%H:%M'),
            'follow_up_date': (now.date() - timedelta(days=1)).isoformat(),
            'chief_complaint': 'Headache',
            'diagnosis': 'Migraine',
        }
        form = MedicalRecordForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('follow_up_date', form.errors)


class AllergyFormTests(MedicalRecordsTestBase):
    """Tests for AllergyForm."""

    def test_valid_form(self):
        form_data = {
            'patient': self.patient.id,
            'allergen': 'Penicillin',
            'severity': 'severe',
            'reaction': 'Rash',
        }
        form = AllergyForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_severity(self):
        form_data = {
            'patient': self.patient.id,
            'allergen': 'Penicillin',
            'severity': 'invalid',
        }
        form = AllergyForm(data=form_data)
        self.assertFalse(form.is_valid())


class VaccinationFormTests(MedicalRecordsTestBase):
    """Tests for VaccinationForm."""

    def test_valid_form(self):
        form_data = {
            'patient': self.patient.id,
            'vaccine': 'covid',
            'dose_number': 1,
            'administration_date': date(2021, 1, 1).isoformat(),
        }
        form = VaccinationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_next_due_date(self):
        form_data = {
            'patient': self.patient.id,
            'vaccine': 'covid',
            'dose_number': 1,
            'administration_date': date(2021, 1, 1).isoformat(),
            'next_due_date': date(2020, 12, 31).isoformat(),
        }
        form = VaccinationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('next_due_date', form.errors)


class FollowUpFormTests(MedicalRecordsTestBase):
    """Tests for FollowUpForm."""

    def test_valid_form(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        now = timezone.now()
        form_data = {
            'medical_record': record.id,
            'scheduled_date': (now + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'),
            'status': 'scheduled',
        }
        form = FollowUpForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_completed_date(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        now = timezone.now()
        scheduled = now + timedelta(days=7)
        form_data = {
            'medical_record': record.id,
            'scheduled_date': scheduled.strftime('%Y-%m-%dT%H:%M'),
            'completed_date': (scheduled - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'status': 'completed',
        }
        form = FollowUpForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('completed_date', form.errors)


class AttachmentFormTests(MedicalRecordsTestBase):
    """Tests for AttachmentForm."""

    def test_valid_form(self):
        file = SimpleUploadedFile("test.pdf", b"file content", content_type="application/pdf")
        form = AttachmentForm(data={'description': 'Test PDF'}, files={'file': file})
        self.assertTrue(form.is_valid())

    def test_invalid_file_extension(self):
        file = SimpleUploadedFile("test.exe", b"file content", content_type="application/x-msdownload")
        form = AttachmentForm(data={'description': 'Test'}, files={'file': file})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)


class ViewTests(MedicalRecordsTestBase):
    """Tests for medical records views."""

    def setUp(self):
        self.client.login(username='doctor1', password='testpass123')

    def test_dashboard_view(self):
        url = reverse('medical_records:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'medical_records/dashboard.html')

    def test_record_list_view(self):
        url = reverse('medical_records:record_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'medical_records/record_list.html')

        response = self.client.get(url, {'q': 'Test'})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {'status': 'active'})
        self.assertEqual(response.status_code, 200)

    # In medical_records/tests.py, replace the test_record_create_view method with:

def test_record_create_view(self):
    url = reverse('medical_records:record_create')
    response = self.client.get(url)
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'medical_records/record_create.html')

    now = timezone.now()
    post_data = {
        'patient': self.patient.id,
        'doctor': self.doctor.id,
        'hospital': self.hospital.id,
        'visit_date': now.strftime('%Y-%m-%dT%H:%M'),
        'chief_complaint': 'Test complaint',
        'symptoms': 'Test symptoms',
        'history_of_present_illness': 'Test history',
        'diagnosis': 'Test diagnosis',
        'clinical_findings': 'Test findings',
        'treatment_plan': 'Test plan',
        'doctor_notes': 'Test notes',
        'status': 'active',
        'appointment': self.appointment.id,
        'prescription': self.prescription.id,
        'lab_order': self.lab_order.id,
    }
    response = self.client.post(url, post_data)
    # Now the view redirects correctly (302) after fixing self.object
    self.assertEqual(response.status_code, 302)
    self.assertTrue(MedicalRecord.objects.filter(diagnosis='Test diagnosis').exists())

    def test_record_detail_view(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        url = reverse('medical_records:record_detail', kwargs={'pk': record.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'medical_records/record_detail.html')
        self.assertEqual(response.context['record'], record)

    def test_record_update_view(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        url = reverse('medical_records:record_edit', kwargs={'pk': record.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        now = timezone.now()
        post_data = {
            'patient': self.patient.id,
            'doctor': self.doctor.id,
            'visit_date': now.strftime('%Y-%m-%dT%H:%M'),
            'chief_complaint': 'Updated complaint',
            'symptoms': 'Updated symptoms',
            'history_of_present_illness': 'Updated history',
            'diagnosis': 'Updated diagnosis',
            'clinical_findings': 'Updated findings',
            'treatment_plan': 'Updated plan',
            'doctor_notes': 'Updated notes',
            'status': 'active',
            'appointment': self.appointment.id,
            'prescription': self.prescription.id,
            'lab_order': self.lab_order.id,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        record.refresh_from_db()
        self.assertEqual(record.diagnosis, 'Updated diagnosis')

    def test_record_delete_view(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Fever',
            diagnosis='Infection'
        )
        url = reverse('medical_records:record_delete', kwargs={'pk': record.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        # View does hard delete
        with self.assertRaises(MedicalRecord.DoesNotExist):
            MedicalRecord.objects.get(pk=record.pk)

    def test_patient_timeline_view(self):
        url = reverse('medical_records:patient_timeline', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'medical_records/timeline.html')


class ServiceTests(MedicalRecordsTestBase):
    """Tests for services.py functions."""

    def test_get_dashboard_stats(self):
        MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Test'
        )
        stats = get_dashboard_stats()
        self.assertIn('total_records', stats)
        self.assertIn('today_visits', stats)
        self.assertIn('active_patients', stats)
        self.assertIn('critical_records', stats)
        self.assertIn('follow_ups_today', stats)

    def test_get_recent_records(self):
        for i in range(5):
            MedicalRecord.objects.create(
                patient=self.patient,
                doctor=self.doctor,
                visit_date=timezone.now() - timedelta(days=i),
                chief_complaint=f'Test {i}',
                diagnosis=f'Diagnosis {i}'
            )
        records = get_recent_records(limit=3)
        self.assertEqual(len(records), 3)

    def test_generate_patient_timeline(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Test'
        )
        timeline = generate_patient_timeline(self.patient)
        self.assertIsInstance(timeline, list)
        self.assertTrue(len(timeline) > 0)
        event = timeline[0]
        self.assertEqual(event['type'], 'record')
        self.assertEqual(event['object'], record)

    def test_get_patient_health_summary(self):
        MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Diagnosis A'
        )
        summary = get_patient_health_summary(self.patient)
        self.assertEqual(summary['total_visits'], 1)
        self.assertEqual(summary['common_diagnosis'][0]['diagnosis'], 'Diagnosis A')

    def test_get_patient_statistics(self):
        MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Test',
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            pulse=72
        )
        stats = get_patient_statistics(self.patient)
        self.assertEqual(stats['total_records'], 1)
        self.assertEqual(stats['avg_blood_pressure_systolic'], 120)

    def test_search_medical_records(self):
        MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Headache',
            diagnosis='Migraine'
        )
        results = search_medical_records('Headache')
        self.assertEqual(results.count(), 1)


class UtilsTests(MedicalRecordsTestBase):
    """Tests for utils.py functions."""

    def test_calculate_bmi(self):
        bmi = calculate_bmi(175, 75)
        self.assertEqual(bmi, 24.49)

    def test_calculate_bmi_with_invalid_input(self):
        self.assertIsNone(calculate_bmi(None, 75))
        self.assertIsNone(calculate_bmi(175, None))
        self.assertIsNone(calculate_bmi(0, 75))

    def test_format_blood_pressure(self):
        self.assertEqual(format_blood_pressure(120, 80), '120/80 mmHg')
        self.assertEqual(format_blood_pressure(None, 80), 'N/A')

    def test_get_bmi_category(self):
        cat = get_bmi_category(22.0)
        self.assertEqual(cat['category'], 'Normal')
        cat = get_bmi_category(32.0)
        self.assertEqual(cat['category'], 'Obese Class I')
        cat = get_bmi_category(None)
        self.assertEqual(cat['category'], 'Unknown')

    def test_calculate_age(self):
        age = calculate_age(date(1990, 1, 1))
        self.assertIsNotNone(age)
        self.assertGreaterEqual(age, 0)

    def test_calculate_bsa(self):
        bsa = calculate_bsa(75, 175)
        self.assertIsNotNone(bsa)
        self.assertAlmostEqual(bsa, 0.191, places=3)

    def test_validate_vital_signs(self):
        data = {'blood_pressure_systolic': 120, 'blood_pressure_diastolic': 80}
        errors = validate_vital_signs(data)
        self.assertEqual(errors, {})
        data['blood_pressure_systolic'] = 20
        errors = validate_vital_signs(data)
        self.assertIn('blood_pressure_systolic', errors)

    def test_calculate_risk_level(self):
        risk = calculate_risk_level(self.patient)
        self.assertIn('level', risk)
        self.assertIn('score', risk)
        self.assertIn('factors', risk)

    def test_generate_medical_record_number(self):
        visit_date = date(2024, 1, 15)
        number = generate_medical_record_number(1, visit_date)
        self.assertEqual(number, 'MR-20240115-P00001')

    def test_safe_decimal(self):
        self.assertEqual(safe_decimal('10.5'), Decimal('10.5'))
        self.assertEqual(safe_decimal('invalid'), Decimal('0.0'))

    def test_format_temperature(self):
        self.assertEqual(format_temperature(98.6), '98.6 °F')
        self.assertEqual(format_temperature(None), 'N/A')


class ValidatorTests(MedicalRecordsTestBase):
    """Tests for validators.py functions."""

    def test_validate_positive_number(self):
        validate_positive_number(5)
        with self.assertRaises(ValidationError):
            validate_positive_number(0)
        with self.assertRaises(ValidationError):
            validate_positive_number(-1)

    def test_validate_weight(self):
        validate_weight(70)
        with self.assertRaises(ValidationError):
            validate_weight(1)
        with self.assertRaises(ValidationError):
            validate_weight(600)

    def test_validate_height(self):
        validate_height(170)
        with self.assertRaises(ValidationError):
            validate_height(20)
        with self.assertRaises(ValidationError):
            validate_height(350)

    def test_validate_blood_pressure_systolic(self):
        validate_blood_pressure_systolic(120)
        with self.assertRaises(ValidationError):
            validate_blood_pressure_systolic(30)

    def test_validate_pulse(self):
        validate_pulse(70)
        with self.assertRaises(ValidationError):
            validate_pulse(10)

    def test_validate_temperature(self):
        validate_temperature(98.6)
        with self.assertRaises(ValidationError):
            validate_temperature(30)

    def test_validate_file_extension(self):
        class MockFile:
            name = 'test.pdf'
        validate_file_extension(MockFile())
        MockFile.name = 'test.exe'
        with self.assertRaises(ValidationError):
            validate_file_extension(MockFile())

    def test_validate_file_size(self):
        class MockFile:
            size = 10 * 1024 * 1024
        validate_file_size(MockFile())
        MockFile.size = 25 * 1024 * 1024
        with self.assertRaises(ValidationError):
            validate_file_size(MockFile())


class SignalTests(TransactionTestCase):
    """Tests for signals.py. Using TransactionTestCase to ensure on_commit runs."""

    def setUp(self):
        # Replicate base setup
        self.user = User.objects.create_user(
            username='doctor1', password='testpass123',
            email='doctor1@example.com', role='doctor'
        )
        self.patient = Patient.objects.create(
            full_name='Test Patient',
            national_id='1234567890',
            date_of_birth='1990-01-01',
            gender='M',
            phone='01712345678',
            address='Dhaka',
            city='Dhaka',
            district='Dhaka'
        )
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            registration_number='HOSP123',
            hospital_type='private',
            ownership='private_owned',
            description='Test Hospital Description',
            full_address='Dhaka, Bangladesh',
            country='Bangladesh',
            division='Dhaka',
            district='Dhaka',
            city='Dhaka',
            email='hospital@test.com',
            phone='01912345678'
        )
        self.doctor = Doctor.objects.create(
            user=self.user,
            hospital=self.hospital,
            full_name='Dr. Test Doctor',
            national_id='0987654321',
            registration_number='REG12345',
            gender='M',
            date_of_birth='1980-01-01',
            phone='01812345678',
            address='Dhaka',
            city='Dhaka',
            district='Dhaka',
            qualification='MBBS'
        )
        self.appointment = Appointment.objects.create(
            hospital=self.hospital,
            doctor=self.doctor,
            patient=self.patient,
            appointment_date=timezone.now().date() + timedelta(days=1),
            appointment_time=timezone.now().time(),
            status=Appointment.Status.COMPLETED,
            appointment_number='APPT-001'
        )

    def test_auto_calculate_bmi_signal(self):
        record = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Test',
            height=175,
            weight=75
        )
        record.save()
        self.assertEqual(record.bmi, 24.49)

    def test_create_follow_up_reminder_signal(self):
        record = MedicalRecord(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Test',
            follow_up_date=timezone.now().date() + timedelta(days=7)
        )
        record.save()
        # In TransactionTestCase, the signal should be triggered by on_commit.
        # We need to force the transaction to commit.
        with transaction.atomic():
            # The signal will run on commit.
            pass
        self.assertTrue(FollowUp.objects.filter(medical_record=record).exists())

    def test_update_medical_record_status_signal(self):
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Test',
            status='active'
        )
        followup = FollowUp.objects.create(
            medical_record=record,
            scheduled_date=timezone.now() + timedelta(days=7),
            status='completed'
        )
        followup.save()
        record.refresh_from_db()
        self.assertEqual(record.status, 'completed')


class PermissionTests(MedicalRecordsTestBase):
    """Tests for role-based permissions."""

    def test_doctor_can_access_own_records(self):
        self.client.login(username='doctor1', password='testpass123')
        url = reverse('medical_records:record_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_doctor_can_delete(self):
        # Doctor has permission to delete (hard delete)
        self.client.login(username='doctor1', password='testpass123')
        record = MedicalRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=timezone.now(),
            chief_complaint='Test',
            diagnosis='Test'
        )
        url = reverse('medical_records:record_delete', kwargs={'pk': record.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        with self.assertRaises(MedicalRecord.DoesNotExist):
            MedicalRecord.objects.get(pk=record.pk)


class URLTests(MedicalRecordsTestBase):
    """Tests for URL patterns."""

    def test_urls_resolve(self):
        url = reverse('medical_records:dashboard')
        self.assertIn('medical-records', url)
        self.assertTrue(url)