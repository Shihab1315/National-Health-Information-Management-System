# pharmacy/tests.py (Part 1)

from django.test import TestCase
from django.core.exceptions import ValidationError

from pharmacy.models import Category, Supplier


# ==========================================================
# CATEGORY TESTS
# ==========================================================

class CategoryModelTest(TestCase):

    def test_create_category(self):
        category = Category.objects.create(
            name="Antibiotic",
            description="Antibiotic medicines"
        )

        self.assertEqual(category.name, "Antibiotic")
        self.assertTrue(category.is_active)
        self.assertIsNotNone(category.slug)

    def test_slug_auto_generated(self):
        category = Category.objects.create(
            name="Pain Killer"
        )

        self.assertEqual(category.slug, "pain-killer")

    def test_string_representation(self):
        category = Category.objects.create(
            name="Vitamin"
        )

        self.assertEqual(str(category), "Vitamin")

    def test_category_ordering(self):
        Category.objects.create(name="Zinc")
        Category.objects.create(name="Antibiotic")

        categories = Category.objects.all()

        self.assertEqual(categories.first().name, "Antibiotic")

    def test_active_manager(self):
        Category.objects.create(
            name="Tablet",
            is_active=True
        )

        Category.objects.create(
            name="Hidden",
            is_active=False
        )

        self.assertEqual(Category.active.count(), 1)

    def test_unique_name(self):
        Category.objects.create(name="Tablet")

        with self.assertRaises(Exception):
            Category.objects.create(name="Tablet")


# ==========================================================
# SUPPLIER TESTS
# ==========================================================

class SupplierModelTest(TestCase):

    def test_create_supplier(self):

        supplier = Supplier.objects.create(
            name="ABC Pharma",
            phone="01711111111",
            email="abc@gmail.com"
        )

        self.assertEqual(
            supplier.name,
            "ABC Pharma"
        )

        self.assertTrue(
            supplier.is_active
        )

    def test_supplier_string(self):

        supplier = Supplier.objects.create(
            name="Square Pharma",
            phone="01888888888"
        )

        self.assertEqual(
            str(supplier),
            "Square Pharma"
        )

    def test_supplier_default_active(self):

        supplier = Supplier.objects.create(
            name="Beximco",
            phone="01999999999"
        )

        self.assertTrue(
            supplier.is_active
        )

    def test_supplier_active_manager(self):

        Supplier.objects.create(
            name="One",
            phone="01711111111",
            is_active=True
        )

        Supplier.objects.create(
            name="Two",
            phone="01822222222",
            is_active=False
        )

        self.assertEqual(
            Supplier.active.count(),
            1
        )

    def test_supplier_update(self):

        supplier = Supplier.objects.create(
            name="Old Supplier",
            phone="01700000000"
        )

        supplier.name = "New Supplier"
        supplier.save()

        supplier.refresh_from_db()

        self.assertEqual(
            supplier.name,
            "New Supplier"
        )

    def test_supplier_blank_email(self):

        supplier = Supplier.objects.create(
            name="Supplier",
            phone="01755555555"
        )

        self.assertEqual(
            supplier.email,
            ""
        )
        # ==========================================================
# MEDICINE MODEL TESTS (Part 2A)
# ==========================================================

from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from pharmacy.models import Category, Medicine


class MedicineModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.category = Category.objects.create(
            name="Antibiotic"
        )

    def create_medicine(self):

        return Medicine.objects.create(
            brand_name="Napa",
            generic_name="Paracetamol",
            category=self.category,
            manufacturer="Beximco",
            dosage_form="tablet",
            strength="500mg",
            unit="pcs",
            buying_price=Decimal("5.00"),
            selling_price=Decimal("8.00"),
            current_stock=100,
            minimum_stock=10,
            maximum_stock=500,
            expiry_date=timezone.now().date() + timedelta(days=365)
        )

    def test_create_medicine(self):

        medicine = self.create_medicine()

        self.assertEqual(
            medicine.brand_name,
            "Napa"
        )

        self.assertEqual(
            medicine.generic_name,
            "Paracetamol"
        )

        self.assertTrue(
            medicine.is_active
        )

    def test_string_representation(self):

        medicine = self.create_medicine()

        self.assertEqual(
            str(medicine),
            "Napa (500mg)"
        )

    def test_auto_generate_medicine_code(self):

        medicine = self.create_medicine()

        self.assertTrue(
            medicine.medicine_code.startswith("MED-")
        )

    def test_auto_generate_barcode(self):

        medicine = self.create_medicine()

        self.assertTrue(
            medicine.barcode.startswith("BAR-")
        )

    def test_profit_margin(self):

        medicine = self.create_medicine()

        self.assertEqual(
            medicine.profit_margin,
            Decimal("3.00")
        )

    def test_low_stock_property(self):

        medicine = self.create_medicine()

        medicine.current_stock = 8
        medicine.save()

        self.assertTrue(
            medicine.is_low_stock
        )

    def test_not_low_stock(self):

        medicine = self.create_medicine()

        self.assertFalse(
            medicine.is_low_stock
        )

    def test_out_of_stock(self):

        medicine = self.create_medicine()

        medicine.current_stock = 0
        medicine.save()

        self.assertTrue(
            medicine.is_out_of_stock
        )

    def test_not_out_of_stock(self):

        medicine = self.create_medicine()

        self.assertFalse(
            medicine.is_out_of_stock
        )

    def test_is_expired_false(self):

        medicine = self.create_medicine()

        self.assertFalse(
            medicine.is_expired
        )
        from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model

from pharmacy.models import (
    Category,
    Medicine,
    Sale,
    SaleItem,
)

User = get_user_model()


class SaleModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="pharmacist",
            password="12345"
        )

        self.category = Category.objects.create(
            name="Tablet"
        )

        self.medicine = Medicine.objects.create(
            brand_name="Napa",
            generic_name="Paracetamol",
            category=self.category,
            dosage_form="tablet",
            strength="500mg",
            buying_price=Decimal("5.00"),
            selling_price=Decimal("8.00"),
            current_stock=100,
            expiry_date=date.today() + timedelta(days=365)
        )

    def test_sale_invoice_generated(self):
        sale = Sale.objects.create(
            pharmacist=self.user,
            total_amount=Decimal("100.00"),
            paid_amount=Decimal("100.00")
        )

        self.assertTrue(sale.invoice_number.startswith("INV-"))

    def test_due_amount_calculation(self):
        sale = Sale.objects.create(
            pharmacist=self.user,
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("300.00")
        )

        self.assertEqual(sale.due_amount, Decimal("200.00"))
        self.assertEqual(sale.payment_status, "partial")

    def test_sale_item_total(self):
        sale = Sale.objects.create(
            pharmacist=self.user,
            total_amount=Decimal("0.00"),
            paid_amount=Decimal("0.00")
        )

        item = SaleItem.objects.create(
            sale=sale,
            medicine=self.medicine,
            quantity=5,
            unit_price=Decimal("8.00")
        )

        self.assertEqual(item.total, Decimal("40.00"))

    def test_calculate_total(self):
        sale = Sale.objects.create(
            pharmacist=self.user,
            total_amount=Decimal("0.00"),
            paid_amount=Decimal("0.00")
        )

        SaleItem.objects.create(
            sale=sale,
            medicine=self.medicine,
            quantity=5,
            unit_price=Decimal("8.00")
        )

        SaleItem.objects.create(
            sale=sale,
            medicine=self.medicine,
            quantity=10,
            unit_price=Decimal("10.00")
        )

        total = sale.calculate_total()

        self.assertEqual(total, Decimal("140.00"))

    def test_negative_discount_validation(self):
        sale = Sale(
            pharmacist=self.user,
            total_amount=Decimal("100"),
            paid_amount=Decimal("50"),
            discount=Decimal("-5")
        )

        with self.assertRaises(Exception):
            sale.full_clean()
            item.full_clean()
from decimal import Decimal
from django.test import TestCase
from pharmacy.models import Sale, SaleItem


class SaleModelTest(TestCase):

    def setUp(self):
        self.sale = Sale.objects.create(
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
        )

    def test_invoice_generated(self):
        self.assertTrue(self.sale.invoice_number.startswith("INV-"))

    def test_due_amount_calculation(self):
        self.assertEqual(self.sale.due_amount, Decimal("0.00"))

    def test_payment_status_paid(self):
        self.assertEqual(self.sale.payment_status, "paid")

    def test_partial_payment(self):
        sale = Sale.objects.create(
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("500.00"),
        )

        self.assertEqual(sale.due_amount, Decimal("500.00"))
        self.assertEqual(sale.payment_status, "partial")

    def test_due_payment(self):
        sale = Sale.objects.create(
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
        )

        self.assertEqual(sale.payment_status, "due")

    def test_paid_amount_greater_than_total(self):
        sale = Sale(
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("600.00"),
        )

        with self.assertRaises(Exception):
            sale.full_clean()

    def test_negative_discount_invalid(self):
        sale = Sale(
            total_amount=Decimal("500"),
            paid_amount=Decimal("500"),
            discount=Decimal("-10")
        )

        with self.assertRaises(Exception):
            sale.full_clean()

    def test_negative_vat_invalid(self):
        sale = Sale(
            total_amount=Decimal("500"),
            paid_amount=Decimal("500"),
            vat=Decimal("-5")
        )

        with self.assertRaises(Exception):
            sale.full_clean()

    def test_string_representation(self):
        self.assertEqual(str(self.sale), self.sale.invoice_number)
# ==========================================================
# SALE ITEM MODEL TESTS
# ==========================================================

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from pharmacy.models import (
    Category,
    Medicine,
    Sale,
    SaleItem,
)


class SaleItemModelTest(TestCase):

    def setUp(self):

        self.category = Category.objects.create(
            name="Tablet"
        )

        self.medicine = Medicine.objects.create(
            brand_name="Napa",
            generic_name="Paracetamol",
            category=self.category,
            dosage_form="tablet",
            strength="500mg",
            buying_price=Decimal("5.00"),
            selling_price=Decimal("8.00"),
            current_stock=100,
            expiry_date="2030-01-01"
        )

        self.sale = Sale.objects.create(
            total_amount=Decimal("0.00"),
            paid_amount=Decimal("0.00")
        )

    def test_create_sale_item(self):

        item = SaleItem.objects.create(
            sale=self.sale,
            medicine=self.medicine,
            quantity=5,
            unit_price=Decimal("8.00")
        )

        self.assertEqual(
            item.total,
            Decimal("40.00")
        )

    def test_total_auto_calculated(self):

        item = SaleItem.objects.create(
            sale=self.sale,
            medicine=self.medicine,
            quantity=10,
            unit_price=Decimal("12.00")
        )

        self.assertEqual(
            item.total,
            Decimal("120.00")
        )

    def test_zero_quantity_invalid(self):

        item = SaleItem(
            sale=self.sale,
            medicine=self.medicine,
            quantity=0,
            unit_price=Decimal("8")
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_negative_price_invalid(self):

        item = SaleItem(
            sale=self.sale,
            medicine=self.medicine,
            quantity=5,
            unit_price=Decimal("-1")
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_string_representation(self):

        item = SaleItem.objects.create(
            sale=self.sale,
            medicine=self.medicine,
            quantity=2,
            unit_price=Decimal("10")
        )

        self.assertEqual(
            item.medicine,
            self.medicine
        )

    def test_quantity_positive_constraint(self):

        item = SaleItem(
            sale=self.sale,
            medicine=self.medicine,
            quantity=-5,
            unit_price=Decimal("10")
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_unit_price_non_negative_constraint(self):

        item = SaleItem(
            sale=self.sale,
            medicine=self.medicine,
            quantity=5,
            unit_price=Decimal("-10")
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_sale_relation(self):

        item = SaleItem.objects.create(
            sale=self.sale,
            medicine=self.medicine,
            quantity=3,
            unit_price=Decimal("15")
        )

        self.assertEqual(
            item.sale,
            self.sale
        )

    def test_medicine_relation(self):

        item = SaleItem.objects.create(
            sale=self.sale,
            medicine=self.medicine,
            quantity=3,
            unit_price=Decimal("15")
        )

        self.assertEqual(
            item.medicine,
            self.medicine
        )
# ==========================================================
# INVENTORY LOG TESTS
# ==========================================================

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from pharmacy.models import (
    Category,
    Supplier,
    Medicine,
    InventoryLog,
)

User = get_user_model()


class InventoryLogModelTest(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="admin",
            password="123456"
        )

        self.category = Category.objects.create(
            name="Tablet"
        )

        self.medicine = Medicine.objects.create(
            brand_name="Napa",
            generic_name="Paracetamol",
            category=self.category,
            dosage_form="tablet",
            strength="500mg",
            buying_price=Decimal("5.00"),
            selling_price=Decimal("8.00"),
            current_stock=100,
            expiry_date=timezone.now().date() + timedelta(days=365)
        )

    def test_create_purchase_log(self):

        log = InventoryLog.objects.create(
            medicine=self.medicine,
            transaction_type="purchase",
            quantity=100,
            created_by=self.user
        )

        self.assertEqual(
            log.transaction_type,
            "purchase"
        )

    def test_create_sale_log(self):

        log = InventoryLog.objects.create(
            medicine=self.medicine,
            transaction_type="sale",
            quantity=-10,
            created_by=self.user
        )

        self.assertEqual(
            log.quantity,
            -10
        )

    def test_string_representation(self):

        log = InventoryLog.objects.create(
            medicine=self.medicine,
            transaction_type="purchase",
            quantity=50,
            created_by=self.user
        )

        expected = f"{self.medicine} - purchase - 50"

        self.assertEqual(
            str(log),
            expected
        )

    def test_inventory_log_ordering(self):

        InventoryLog.objects.create(
            medicine=self.medicine,
            transaction_type="purchase",
            quantity=5,
            created_by=self.user
        )

        InventoryLog.objects.create(
            medicine=self.medicine,
            transaction_type="sale",
            quantity=-2,
            created_by=self.user
        )

        logs = InventoryLog.objects.all()

        self.assertEqual(
            logs.count(),
            2
        )


# ==========================================================
# ACTIVE MANAGER TESTS
# ==========================================================

class ActiveManagerTest(TestCase):

    def test_category_active_manager(self):

        Category.objects.create(
            name="Tablet",
            is_active=True
        )

        Category.objects.create(
            name="Hidden",
            is_active=False
        )

        self.assertEqual(
            Category.active.count(),
            1
        )

    def test_supplier_active_manager(self):

        Supplier.objects.create(
            name="ABC",
            phone="01711111111",
            is_active=True
        )

        Supplier.objects.create(
            name="XYZ",
            phone="01811111111",
            is_active=False
        )

        self.assertEqual(
            Supplier.active.count(),
            1
        )

    def test_medicine_active_manager(self):

        category = Category.objects.create(
            name="Tablet"
        )

        Medicine.objects.create(
            brand_name="Napa",
            category=category,
            dosage_form="tablet",
            buying_price=Decimal("5"),
            selling_price=Decimal("8"),
            expiry_date=timezone.now().date() + timedelta(days=365),
            is_active=True
        )

        Medicine.objects.create(
            brand_name="Old Medicine",
            category=category,
            dosage_form="tablet",
            buying_price=Decimal("5"),
            selling_price=Decimal("8"),
            expiry_date=timezone.now().date() + timedelta(days=365),
            is_active=False
        )

        self.assertEqual(
            Medicine.active.count(),
            1
        )