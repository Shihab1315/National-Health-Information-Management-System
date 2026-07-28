import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone

from .models import Medicine, Sale, PurchaseOrder, InventoryLog, Category, Supplier, SaleItem

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Dashboard Statistics (Optimized)
# ----------------------------------------------------------------------
def get_dashboard_stats():
    """
    Retrieve dashboard statistics with optimized queries.
    Uses aggregation and annotation to reduce database hits.
    """
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    # All medicines active
    active_meds = Medicine.objects.filter(is_active=True)

    # Counts using aggregate
    stats = active_meds.aggregate(
        total_medicines=Count('id'),
        low_stock=Count('id', filter=Q(current_stock__lte=F('minimum_stock'))),
        out_of_stock=Count('id', filter=Q(current_stock=0)),
        expired=Count('id', filter=Q(expiry_date__lt=today)),
    )

    # Supplier count
    total_suppliers = Supplier.objects.filter(is_active=True).count()

    # Sales totals
    sales_today = Sale.objects.filter(sale_date__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
    sales_month = Sale.objects.filter(sale_date__date__gte=start_of_month).aggregate(total=Sum('total_amount'))['total'] or 0
    total_revenue = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    # Purchases this month
    purchases_month = PurchaseOrder.objects.filter(purchase_date__gte=start_of_month).aggregate(total=Sum('total_amount'))['total'] or 0

    return {
        'total_medicines': stats['total_medicines'] or 0,
        'low_stock': stats['low_stock'] or 0,
        'out_of_stock': stats['out_of_stock'] or 0,
        'expired': stats['expired'] or 0,
        'suppliers': total_suppliers,
        'today_sales': sales_today,
        'monthly_sales': sales_month,
        'total_revenue': total_revenue,
        'total_purchases': purchases_month,
    }


# ----------------------------------------------------------------------
# Recent Activity Helpers (Optimized with select_related)
# ----------------------------------------------------------------------
def get_recent_sales(limit=5):
    """Return recent sales with related patient and pharmacist."""
    return Sale.objects.select_related('patient', 'pharmacist').order_by('-sale_date')[:limit]


def get_recent_purchases(limit=5):
    """Return recent purchases with related supplier."""
    return PurchaseOrder.objects.select_related('supplier').order_by('-purchase_date')[:limit]


# ----------------------------------------------------------------------
# Stock Update (Atomic & Concurrency-Safe)
# ----------------------------------------------------------------------
@transaction.atomic
def update_stock(medicine, quantity, transaction_type, reference='', user=None):
    """
    Update stock and log inventory movement atomically.
    Uses select_for_update to prevent race conditions.
    quantity: positive for in, negative for out.
    """
    # Lock the medicine row for update
    medicine = Medicine.objects.select_for_update().get(pk=medicine.pk)

    # Validate stock availability for negative movements
    if quantity < 0 and medicine.current_stock + quantity < 0:
        raise ValidationError(
            f"Insufficient stock for {medicine.brand_name}. "
            f"Available: {medicine.current_stock}, Required: {-quantity}"
        )

    # Update stock
    medicine.current_stock += quantity
    medicine.save(update_fields=['current_stock', 'updated_at'])

    # Log the transaction
    InventoryLog.objects.create(
        medicine=medicine,
        transaction_type=transaction_type,
        quantity=quantity,
        reference=reference,
        created_by=user
    )

    logger.info(
        f"Inventory {transaction_type}: {medicine.brand_name} "
        f"quantity={quantity}, new_stock={medicine.current_stock}, "
        f"reference={reference}, user={user}"
    )

    return medicine


# ----------------------------------------------------------------------
# Enterprise Inventory Service
# ----------------------------------------------------------------------
class InventoryService:
    """Enterprise service for inventory operations."""

    @staticmethod
    def get_stock_levels(medicine_ids=None):
        """Return stock levels with annotations."""
        qs = Medicine.objects.filter(is_active=True)
        if medicine_ids:
            qs = qs.filter(id__in=medicine_ids)
        return qs.values('id', 'brand_name', 'current_stock', 'minimum_stock', 'maximum_stock')

    @staticmethod
    def get_expiry_alert(days=30):
        """Return medicines expiring within given days."""
        today = timezone.now().date()
        expiry_limit = today + timezone.timedelta(days=days)
        return Medicine.objects.filter(
            expiry_date__lte=expiry_limit,
            expiry_date__gte=today,
            is_active=True
        ).select_related('category')

    @staticmethod
    def get_low_stock_alert():
        """Return medicines where current_stock <= minimum_stock."""
        return Medicine.objects.filter(
            current_stock__lte=F('minimum_stock'),
            is_active=True
        ).select_related('category')

    @staticmethod
    def get_out_of_stock():
        """Return medicines with zero stock."""
        return Medicine.objects.filter(current_stock=0, is_active=True).select_related('category')

    @staticmethod
    def reconcile_inventory(medicine_id, expected_quantity, reference='reconciliation', user=None):
        """
        Manually adjust stock to expected quantity.
        Creates an adjustment log with the difference.
        """
        with transaction.atomic():
            medicine = Medicine.objects.select_for_update().get(pk=medicine_id)
            diff = expected_quantity - medicine.current_stock
            if diff != 0:
                update_stock(medicine, diff, 'adjustment', reference, user)
            return medicine

    @staticmethod
    def reserve_stock(medicine_id, quantity, reservation_reference, user=None):
        """
        Reserve stock for future use (placeholder for future feature).
        Currently, this just validates availability.
        """
        medicine = Medicine.objects.get(pk=medicine_id)
        if quantity > medicine.current_stock:
            raise ValidationError(
                f"Insufficient stock for {medicine.brand_name}. "
                f"Available: {medicine.current_stock}, Requested: {quantity}"
            )
        # In a real system, you'd have a Reservation model.
        # For now, we just validate.
        return True


# ----------------------------------------------------------------------
# Enterprise Sales Analytics Service
# ----------------------------------------------------------------------
class SalesAnalyticsService:
    """Analytics for sales data."""

    @staticmethod
    def get_daily_sales(date=None):
        """Get sales for a specific day (default today)."""
        if date is None:
            date = timezone.now().date()
        return Sale.objects.filter(sale_date__date=date).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )

    @staticmethod
    def get_monthly_sales(year, month):
        """Get sales for a specific month/year."""
        start = timezone.datetime(year, month, 1)
        end = (start.replace(month=month+1) if month < 12 else start.replace(year=year+1, month=1))
        return Sale.objects.filter(
            sale_date__gte=start,
            sale_date__lt=end
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )

    @staticmethod
    def get_top_selling_medicines(limit=10):
        """Get top selling medicines by quantity sold."""
        return SaleItem.objects.values('medicine__brand_name', 'medicine_id').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total')
        ).order_by('-total_quantity')[:limit]

    @staticmethod
    def get_sales_by_payment_method(start_date=None, end_date=None):
        """Aggregate sales by payment method."""
        qs = Sale.objects.all()
        if start_date:
            qs = qs.filter(sale_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(sale_date__date__lte=end_date)
        return qs.values('payment_method').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')


# ----------------------------------------------------------------------
# Enterprise Purchase Analytics Service
# ----------------------------------------------------------------------
class PurchaseAnalyticsService:
    """Analytics for purchase data."""

    @staticmethod
    def get_monthly_purchases(year, month):
        start = timezone.datetime(year, month, 1)
        end = (start.replace(month=month+1) if month < 12 else start.replace(year=year+1, month=1))
        return PurchaseOrder.objects.filter(
            purchase_date__gte=start,
            purchase_date__lt=end
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )

    @staticmethod
    def get_top_suppliers(limit=10):
        """Top suppliers by purchase amount."""
        return PurchaseOrder.objects.values('supplier__name', 'supplier_id').annotate(
            total_spent=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('-total_spent')[:limit]


# ----------------------------------------------------------------------
# Enterprise Analytics Combined (Revenue, Profit, etc.)
# ----------------------------------------------------------------------
class RevenueAnalyticsService:
    """Revenue and profit analytics."""

    @staticmethod
    def get_gross_profit(start_date=None, end_date=None):
        """
        Estimate gross profit from sales.
        This is a simplified version; actual profit would consider buying_price per sale.
        """
        qs = SaleItem.objects.all()
        if start_date:
            qs = qs.filter(sale__sale_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(sale__sale_date__date__lte=end_date)
        # Profit per item = (unit_price - medicine.buying_price) * quantity
        # Use annotation for aggregation
        return qs.annotate(
            profit=F('unit_price') - F('medicine__buying_price'),
            total_profit=F('profit') * F('quantity')
        ).aggregate(total_profit=Sum('total_profit'))['total_profit'] or 0


# ----------------------------------------------------------------------
# Legacy Functions (kept for backward compatibility)
# ----------------------------------------------------------------------
# The following functions are retained as aliases to the new services
# to avoid breaking existing views. They are now thin wrappers.
def get_dashboard_stats_legacy():
    """Legacy wrapper; use get_dashboard_stats instead."""
    return get_dashboard_stats()

def get_recent_sales_legacy(limit=5):
    """Legacy wrapper; use get_recent_sales."""
    return get_recent_sales(limit)

def get_recent_purchases_legacy(limit=5):
    """Legacy wrapper; use get_recent_purchases."""
    return get_recent_purchases(limit)

# Note: update_stock is already provided above and should be used directly.