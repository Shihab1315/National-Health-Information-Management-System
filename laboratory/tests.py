# laboratory/tests.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from .models import TestCategory, LaboratoryTest, LabOrder, LabOrderItem, LabResult
from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital

User = get_user_model()


class LaboratoryModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='labadmin', password='testpass123')
        self.category = TestCategory.objects.create(name='Biochemistry')
        self.test = LaboratoryTest.objects.create(
            category=self.category,
            test_code='GLU',
            name='Glucose',
            normal_range='3.5–5.5',
            unit='mmol/L',
            price=100.00
        )
        self.patient = Patient.objects.create(
            full_name='Rahim Test',
            national_id='1234567890',
            date_of_birth='1990-01-01',
            gender='M',
            phone='01712345678',
            address='Dhaka',
            city='Dhaka',
            district='Dhaka'
        )
        self.doctor = Doctor.objects.create(
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
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            registration_number='HOSP123',
            hospital_type='private',
            ownership='private_owned',
            description='Test',
            full_address='Dhaka',
            country='Bangladesh',
            division='Dhaka',
            district='Dhaka',
            city='Dhaka',
            email='hospital@test.com',
            phone='01912345678'
        )

    def test_test_creation(self):
        self.assertEqual(self.test.name, 'Glucose')
        self.assertTrue(self.test.is_active)

    def test_test_code_manual_setting(self):
        self.assertEqual(self.test.test_code, 'GLU')

    def test_order_creation(self):
        order = LabOrder.objects.create(
        appointment=self.appointment, # pyright: ignore[reportAttributeAccessIssue]
        patient=self.patient,
        doctor=self.doctor,
        created_by=self.user
)
        self.assertIsNotNone(order.order_number)
        self.assertTrue(order.order_number.startswith('LAB-'))

    def test_order_item_creation(self):
        order = LabOrder.objects.create(
            appointment=self.appointment,
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital,
            created_by=self.user
        )
        item = LabOrderItem.objects.create(
            lab_order=order,
            test=self.test,
            notes="Test note"
        )
        self.assertEqual(item.test, self.test)
        self.assertEqual(item.lab_order, order)

    def test_result_creation(self):
        order = LabOrder.objects.create(
            appointment=self.appointment,
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital,
            created_by=self.user
        )
        item = LabOrderItem.objects.create(
            lab_order=order,
            test=self.test
        )
        result = LabResult.objects.create(
            order_item=item,
            result='5.2',
            interpretation='Normal',
            remarks='Test remark',
            technician=self.user
        )
        self.assertEqual(result.result, '5.2')
        self.assertEqual(result.interpretation, 'Normal')
        self.assertEqual(result.order_item, item)

    def test_order_status_update(self):
        order = LabOrder.objects.create(
            appointment=self.appointment,
            patient=self.patient,
            doctor=self.doctor,
            hospital=self.hospital,
            status=LabOrder.Status.ORDERED,
            created_by=self.user
        )
        order.status = LabOrder.Status.COLLECTED
        order.save()
        self.assertEqual(order.status, LabOrder.Status.COLLECTED)


class LaboratoryViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='labuser', password='testpass123')
        self.client.login(username='labuser', password='testpass123')
        self.category = TestCategory.objects.create(name='Biochemistry')
        self.test = LaboratoryTest.objects.create(
            category=self.category,
            test_code='GLU',
            name='Glucose',
            normal_range='3.5–5.5',
            unit='mmol/L',
            price=100.00
        )

    def test_dashboard_view(self):
        response = self.client.get(reverse('laboratory:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'laboratory/dashboard.html')

    def test_test_list_view(self):
        response = self.client.get(reverse('laboratory:test_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Glucose')

    def test_test_create_view(self):
        response = self.client.post(reverse('laboratory:test_create'), {
            'category': self.category.pk,
            'test_code': 'HBA1C',
            'name': 'HbA1c',
            'normal_range': '4.0–5.6',
            'unit': '%',
            'price': 150.00,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LaboratoryTest.objects.filter(name='HbA1c').exists())

    def test_test_update_view(self):
        response = self.client.post(reverse('laboratory:test_update', args=[self.test.pk]), {
            'category': self.category.pk,
            'test_code': 'GLU',
            'name': 'Glucose Updated',
            'normal_range': '3.5–5.6',
            'unit': 'mmol/L',
            'price': 120.00,
        })
        self.test.refresh_from_db()
        self.assertEqual(self.test.name, 'Glucose Updated')

    def test_test_delete_view(self):
        response = self.client.post(reverse('laboratory:test_delete', args=[self.test.pk]))
        self.assertEqual(response.status_code, 302)
        self.test.refresh_from_db()
        self.assertIsNotNone(self.test.deleted_at)