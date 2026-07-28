from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    Category, Supplier, Medicine, InventoryLog,
    PurchaseOrder, PurchaseItem, Sale, SaleItem
)


# ----------------------------------------------------------------------
# Inlines
# ----------------------------------------------------------------------
class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    min_num = 0
    fields = ('medicine', 'quantity', 'unit_price', 'total')
    readonly_fields = ('total',)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    min_num = 0
    fields = ('medicine', 'quantity', 'unit_price', 'total')
    readonly_fields = ('total',)


# ----------------------------------------------------------------------
# Category Admin
# ----------------------------------------------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)


# ----------------------------------------------------------------------
# Supplier Admin
# ----------------------------------------------------------------------
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'phone', 'email', 'is_active')
    search_fields = ('name', 'company')
    list_filter = ('is_active',)
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} supplier(s) activated.")
    make_active.short_description = "Activate selected suppliers"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} supplier(s) deactivated.")
    make_inactive.short_description = "Deactivate selected suppliers"


# ----------------------------------------------------------------------
# Medicine Admin
# ----------------------------------------------------------------------
@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        'brand_name', 'medicine_code', 'category', 'current_stock',
        'stock_status', 'expiry_status', 'selling_price', 'profit_display',
        'is_active'
    )
    list_filter = ('category', 'dosage_form', 'is_active', 'expiry_date')
    search_fields = ('brand_name', 'generic_name', 'medicine_code', 'barcode')
    readonly_fields = ('medicine_code', 'barcode', 'created_at', 'updated_at')
    list_select_related = ('category',)
    autocomplete_fields = ('category',)
    list_per_page = 50
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_display_links = ('brand_name',)
    empty_value_display = '-'
    actions = ['make_active', 'make_inactive']

    # ---- Stock & Expiry Badges ----
    def stock_status(self, obj):
        if obj.current_stock == 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.current_stock <= obj.minimum_stock:
            return format_html('<span style="color: orange;">Low Stock</span>')
        return format_html('<span style="color: green;">In Stock</span>')
    stock_status.short_description = 'Stock Status'

    def expiry_status(self, obj):
        if obj.expiry_date < timezone.now().date():
            return format_html('<span style="color: red;">Expired</span>')
        elif (obj.expiry_date - timezone.now().date()).days <= 30:
            return format_html('<span style="color: orange;">Expiring Soon</span>')
        return format_html('<span style="color: green;">Valid</span>')
    expiry_status.short_description = 'Expiry Status'

    def profit_display(self, obj):
        profit = obj.profit_margin
        if profit >= 0:
            return format_html('<span style="color: green;">+{} Tk</span>', profit)
        return format_html('<span style="color: red;">{} Tk</span>', profit)
    profit_display.short_description = 'Profit Margin'

    # ---- Bulk actions ----
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} medicine(s) activated.")
    make_active.short_description = "Activate selected medicines"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} medicine(s) deactivated.")
    make_inactive.short_description = "Deactivate selected medicines"


# ----------------------------------------------------------------------
# PurchaseOrder Admin
# ----------------------------------------------------------------------
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        'purchase_number', 'supplier', 'purchase_date',
        'total_amount', 'payment_status_colored'
    )
    list_filter = ('payment_status', 'purchase_date')
    search_fields = ('purchase_number', 'invoice_number')
    inlines = [PurchaseItemInline]
    list_select_related = ('supplier',)
    autocomplete_fields = ('supplier',)
    date_hierarchy = 'purchase_date'
    list_per_page = 50
    ordering = ('-purchase_date',)
    empty_value_display = '-'
    actions = ['recalculate_total']

    def payment_status_colored(self, obj):
        color = {
            'paid': 'green',
            'partial': 'orange',
            'due': 'red'
        }.get(obj.payment_status, 'gray')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_payment_status_display())
    payment_status_colored.short_description = 'Payment Status'
    payment_status_colored.admin_order_field = 'payment_status'

    def recalculate_total(self, request, queryset):
        for order in queryset:
            order.calculate_total()
        self.message_user(request, f"Recalculated totals for {queryset.count()} purchase order(s).")
    recalculate_total.short_description = "Recalculate total for selected orders"


# ----------------------------------------------------------------------
# Sale Admin
# ----------------------------------------------------------------------
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'patient', 'pharmacist', 'sale_date',
        'total_amount', 'payment_status_colored'
    )
    list_filter = ('payment_status', 'sale_date')
    search_fields = ('invoice_number', 'patient__full_name')
    inlines = [SaleItemInline]
    list_select_related = ('patient', 'pharmacist', 'prescription')
    autocomplete_fields = ('patient', 'pharmacist', 'prescription')
    date_hierarchy = 'sale_date'
    list_per_page = 50
    ordering = ('-sale_date',)
    empty_value_display = '-'
    actions = ['recalculate_total']

    def payment_status_colored(self, obj):
        color = {
            'paid': 'green',
            'partial': 'orange',
            'due': 'red'
        }.get(obj.payment_status, 'gray')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_payment_status_display())
    payment_status_colored.short_description = 'Payment Status'
    payment_status_colored.admin_order_field = 'payment_status'

    def recalculate_total(self, request, queryset):
        for sale in queryset:
            sale.calculate_total()
        self.message_user(request, f"Recalculated totals for {queryset.count()} sale(s).")
    recalculate_total.short_description = "Recalculate total for selected sales"


# ----------------------------------------------------------------------
# InventoryLog Admin
# ----------------------------------------------------------------------
@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'transaction_type', 'quantity', 'created_at')
    list_filter = ('transaction_type',)
    list_select_related = ('medicine', 'created_by')
    search_fields = ('medicine__brand_name', 'medicine__generic_name', 'reference')
    date_hierarchy = 'created_at'
    list_per_page = 50
    ordering = ('-created_at',)
    empty_value_display = '-'