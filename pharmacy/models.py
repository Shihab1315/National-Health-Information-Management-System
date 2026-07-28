from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from doctors.models import Doctor
from patients.models import Patient
from prescriptions.models import Prescription

User = get_user_model()


# ----------------------------------------------------------------------
# Custom Manager for active records
# ----------------------------------------------------------------------
class ActiveManager(models.Manager):
    """Manager to filter only active records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


# ----------------------------------------------------------------------
# Category
# ----------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ----------------------------------------------------------------------
# Supplier
# ----------------------------------------------------------------------
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    trade_license = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        ordering = ['name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


# ----------------------------------------------------------------------
# Medicine
# ----------------------------------------------------------------------
class Medicine(models.Model):
    DOSAGE_FORM_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('ointment', 'Ointment'),
        ('drop', 'Drop'),
        ('inhaler', 'Inhaler'),
        ('cream', 'Cream'),
        ('gel', 'Gel'),
        ('spray', 'Spray'),
        ('powder', 'Powder'),
        ('other', 'Other'),
    ]

    medicine_code = models.CharField(max_length=20, unique=True, blank=True)
    barcode = models.CharField(max_length=50, unique=True, blank=True)
    qr_code = models.ImageField(upload_to='pharmacy/qr/', blank=True, null=True)
    brand_name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='medicines')
    manufacturer = models.CharField(max_length=200, blank=True)
    dosage_form = models.CharField(max_length=20, choices=DOSAGE_FORM_CHOICES, default='tablet')
    strength = models.CharField(max_length=50, blank=True, help_text="e.g., 500mg")
    unit = models.CharField(max_length=20, default='pcs', help_text="e.g., pcs, ml, mg")
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=10)
    maximum_stock = models.PositiveIntegerField(default=100)
    expiry_date = models.DateField()
    batch_number = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='pharmacy/medicines/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        ordering = ['brand_name']
        verbose_name = 'Medicine'
        verbose_name_plural = 'Medicines'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['manufacturer']),
            models.Index(fields=['dosage_form']),
            models.Index(fields=['medicine_code']),
            models.Index(fields=['barcode']),
        ]

    def __str__(self):
        return f"{self.brand_name} ({self.strength})"

    def clean(self):
        if self.expiry_date and self.expiry_date < timezone.now().date():
            raise ValidationError({'expiry_date': 'Expiry date cannot be in the past.'})
        if self.buying_price < 0:
            raise ValidationError({'buying_price': 'Buying price cannot be negative.'})
        if self.selling_price < 0:
            raise ValidationError({'selling_price': 'Selling price cannot be negative.'})
        if self.selling_price < self.buying_price:
            raise ValidationError({'selling_price': 'Selling price must be at least buying price.'})

    def save(self, *args, **kwargs):
        import random

        if not self.medicine_code:
            for _ in range(10):
                code = f"MED-{random.randint(1000, 9999)}"
                if not Medicine.objects.filter(medicine_code=code).exists():
                    self.medicine_code = code
                    break
            else:
                raise ValueError("Unable to generate unique medicine_code after 10 attempts.")

        if not self.barcode:
            for _ in range(10):
                code = f"BAR-{random.randint(10000, 99999)}"
                if not Medicine.objects.filter(barcode=code).exists():
                    self.barcode = code
                    break
            else:
                raise ValueError("Unable to generate unique barcode after 10 attempts.")

        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock

    @property
    def is_out_of_stock(self):
        return self.current_stock == 0

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def profit_margin(self):
        if self.buying_price:
            return self.selling_price - self.buying_price
        return 0


# ----------------------------------------------------------------------
# InventoryLog
# ----------------------------------------------------------------------
class InventoryLog(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('expiry', 'Expiry'),
    ]
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='inventory_logs')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()  # positive for in, negative for out
    reference = models.CharField(max_length=100, blank=True, help_text="e.g., Purchase Order # or Sale Invoice #")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inventory Log'
        verbose_name_plural = 'Inventory Logs'
        indexes = [
            models.Index(fields=['medicine']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.medicine} - {self.transaction_type} - {self.quantity}"


# ----------------------------------------------------------------------
# PurchaseOrder
# ----------------------------------------------------------------------
class PurchaseOrder(models.Model):
    PAYMENT_STATUS = [
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('due', 'Due'),
    ]
    purchase_number = models.CharField(max_length=20, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    purchase_date = models.DateField(default=timezone.now)
    invoice_number = models.CharField(max_length=50, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='due')
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-purchase_date']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        indexes = [
            models.Index(fields=['supplier']),
            models.Index(fields=['purchase_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['purchase_number']),
        ]

    def __str__(self):
        return self.purchase_number

    def clean(self):
        if self.discount < 0:
            raise ValidationError({'discount': 'Discount cannot be negative.'})
        if self.vat < 0:
            raise ValidationError({'vat': 'VAT cannot be negative.'})
        if self.total_amount < 0:
            raise ValidationError({'total_amount': 'Total amount cannot be negative.'})

    def save(self, *args, **kwargs):
        import random
        if not self.purchase_number:
            for _ in range(10):
                num = f"PO-{random.randint(1000, 9999)}"
                if not PurchaseOrder.objects.filter(purchase_number=num).exists():
                    self.purchase_number = num
                    break
            else:
                raise ValueError("Unable to generate unique purchase_number after 10 attempts.")
        super().save(*args, **kwargs)

    def calculate_total(self):
        items = PurchaseItem.objects.filter(purchase=self)
        total = sum(item.total for item in items)
        total = total - self.discount + self.vat
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total


# ----------------------------------------------------------------------
# PurchaseItem
# ----------------------------------------------------------------------
class PurchaseItem(models.Model):
    purchase = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=Decimal("0.00"))

    class Meta:
        verbose_name = 'Purchase Item'
        verbose_name_plural = 'Purchase Items'
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name='purchase_item_quantity_positive'),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name='purchase_item_unit_price_non_negative'),
        ]
        indexes = [
            models.Index(fields=['purchase']),
            models.Index(fields=['medicine']),
        ]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be positive.'})
        if self.unit_price < 0:
            raise ValidationError({'unit_price': 'Unit price cannot be negative.'})

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


# ----------------------------------------------------------------------
# Sale
# ----------------------------------------------------------------------
class Sale(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile', 'Mobile Banking'),
        ('due', 'Due'),
    ]
    PAYMENT_STATUS = [
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('due', 'Due'),
    ]
    invoice_number = models.CharField(max_length=20, unique=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    pharmacist = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    sale_date = models.DateTimeField(default=timezone.now)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    due_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='paid')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sale_date']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['sale_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['pharmacist']),
            models.Index(fields=['invoice_number']),
        ]

    def __str__(self):
        return self.invoice_number

    def clean(self):
        if self.discount < 0:
            raise ValidationError({'discount': 'Discount cannot be negative.'})
        if self.vat < 0:
            raise ValidationError({'vat': 'VAT cannot be negative.'})
        if self.paid_amount < 0:
            raise ValidationError({'paid_amount': 'Paid amount cannot be negative.'})
        if self.paid_amount > self.total_amount:
            raise ValidationError({'paid_amount': 'Paid amount cannot exceed total amount.'})

    def save(self, *args, **kwargs):
        import random
        if not self.invoice_number:
            for _ in range(10):
                num = f"INV-{random.randint(10000, 99999)}"
                if not Sale.objects.filter(invoice_number=num).exists():
                    self.invoice_number = num
                    break
            else:
                raise ValueError("Unable to generate unique invoice_number after 10 attempts.")

        self.due_amount = self.total_amount - self.paid_amount
        if self.due_amount <= 0:
            self.payment_status = 'paid'
        elif self.paid_amount > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'due'
        super().save(*args, **kwargs)

    def calculate_total(self):
        total = sum(item.total for item in SaleItem.objects.filter(sale=self))
        total = total - self.discount + self.vat
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total


# ----------------------------------------------------------------------
# SaleItem
# ----------------------------------------------------------------------
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=Decimal("0.00"))

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name='sale_item_quantity_positive'),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name='sale_item_unit_price_non_negative'),
        ]
        indexes = [
            models.Index(fields=['sale']),
            models.Index(fields=['medicine']),
        ]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be positive.'})
        if self.unit_price < 0:
            raise ValidationError({'unit_price': 'Unit price cannot be negative.'})

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)