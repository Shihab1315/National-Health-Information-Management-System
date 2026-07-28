import logging
from decimal import Decimal
from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Q, F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.decorators import role_required
from .forms import MedicineForm, PurchaseOrderForm, SaleForm, SupplierForm
from .models import Category, InventoryLog, Medicine, PurchaseOrder, Sale, SaleItem, Supplier
from .services import get_dashboard_stats, get_recent_purchases, get_recent_sales, update_stock

# Setup logger
logger = logging.getLogger(__name__)


# -------------------- Dashboard --------------------
@login_required
@role_required(['super_admin', 'hospital_admin', 'pharmacist'])
def dashboard(request):
    """Dashboard view with stats and recent activity."""
    try:
        stats = get_dashboard_stats()
        recent_sales = get_recent_sales(5)
        recent_purchases = get_recent_purchases(5)
        context = {
            'stats': stats,
            'recent_sales': recent_sales,
            'recent_purchases': recent_purchases,
        }
        return render(request, 'pharmacy/dashboard.html', context)
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        messages.error(request, "Unable to load dashboard. Please try again.")
        return render(request, 'pharmacy/dashboard.html', {'stats': {}, 'recent_sales': [], 'recent_purchases': []})


# -------------------- Medicine CRUD --------------------
class MedicineListView(LoginRequiredMixin, ListView):
    model = Medicine
    template_name = 'pharmacy/medicine_list.html'
    context_object_name = 'medicines'
    paginate_by = 12

    def get_queryset(self):
        # Optimize with select_related and prefetch
        qs = super().get_queryset().select_related('category').prefetch_related('inventory_logs')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(brand_name__icontains=q) |
                Q(generic_name__icontains=q) |
                Q(medicine_code__icontains=q) |
                Q(barcode__icontains=q)
            )
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category__id=category)
        stock_status = self.request.GET.get('stock')
        if stock_status == 'low':
            qs = qs.filter(current_stock__lte=models.F('minimum_stock'))
        elif stock_status == 'out':
            qs = qs.filter(current_stock=0)
        expiry = self.request.GET.get('expiry')
        if expiry == 'expired':
            qs = qs.filter(expiry_date__lt=timezone.now().date())
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Optimize category queryset
        context['categories'] = Category.objects.filter(is_active=True).only('id', 'name')
        # Add extra context for filtering
        context['current_q'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_stock'] = self.request.GET.get('stock', '')
        context['current_expiry'] = self.request.GET.get('expiry', '')
        return context


class MedicineCreateView(LoginRequiredMixin, CreateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'pharmacy/medicine_create.html'
    success_url = reverse_lazy('pharmacy:medicine_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            medicine = cast(Medicine, form.instance)
            messages.success(self.request, 'Medicine added successfully.')
            logger.info(f"Medicine created: {medicine.brand_name} by {self.request.user}")
            return response
        except Exception as e:
            logger.error(f"Medicine creation failed: {e}", exc_info=True)
            messages.error(self.request, "Failed to add medicine. Please try again.")
            return self.form_invalid(form)


class MedicineDetailView(LoginRequiredMixin, DetailView):
    model = Medicine
    template_name = 'pharmacy/medicine_detail.html'
    context_object_name = 'medicine'

    def get_queryset(self):
        # Optimize with select_related
        return super().get_queryset().select_related('category')


class MedicineUpdateView(LoginRequiredMixin, UpdateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'pharmacy/medicine_edit.html'
    success_url = reverse_lazy('pharmacy:medicine_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            medicine = cast(Medicine, form.instance)
            messages.success(self.request, 'Medicine updated successfully.')
            logger.info(f"Medicine updated: {medicine.brand_name} by {self.request.user}")
            return response
        except Exception as e:
            logger.error(f"Medicine update failed: {e}", exc_info=True)
            messages.error(self.request, "Failed to update medicine. Please try again.")
            return self.form_invalid(form)


class MedicineDeleteView(LoginRequiredMixin, DeleteView):
    model = Medicine
    template_name = 'pharmacy/medicine_confirm_delete.html'
    success_url = reverse_lazy('pharmacy:medicine_list')

    def delete(self, request, *args, **kwargs):
        try:
            medicine = cast(Medicine, self.get_object())
            logger.warning(f"Medicine deleted: {medicine.brand_name} by {request.user}")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Medicine deletion failed: {e}", exc_info=True)
            messages.error(request, "Failed to delete medicine. Please try again.")
            return redirect('pharmacy:medicine_list')


# -------------------- Inventory --------------------
@login_required
@role_required(['super_admin', 'hospital_admin', 'pharmacist'])
def inventory_view(request):
    # Optimized with select_related and filtering
    medicines = Medicine.objects.filter(is_active=True).select_related('category').order_by('brand_name')
    # Filter by category, expiry, etc.
    category_id = request.GET.get('category')
    if category_id:
        medicines = medicines.filter(category_id=category_id)
    expiry_filter = request.GET.get('expiry')
    if expiry_filter == 'expired':
        medicines = medicines.filter(expiry_date__lt=timezone.now().date())
    elif expiry_filter == 'expiring_soon':
        # Within 30 days
        future_date = timezone.now().date() + timezone.timedelta(days=30)
        medicines = medicines.filter(expiry_date__lte=future_date, expiry_date__gte=timezone.now().date())

    # Pagination
    paginator = Paginator(medicines, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'medicines': page_obj,
        'categories': Category.objects.filter(is_active=True).only('id', 'name'),
        'current_category': category_id,
        'current_expiry': expiry_filter,
    }
    return render(request, 'pharmacy/inventory.html', context)


# -------------------- Suppliers --------------------
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'pharmacy/suppliers.html'
    context_object_name = 'suppliers'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(company__icontains=q) | Q(phone__icontains=q))
        return qs


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'pharmacy/supplier_form.html'
    success_url = reverse_lazy('pharmacy:supplier_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            supplier_name = form.instance.name
            messages.success(self.request, 'Supplier added successfully.')
            logger.info(f"Supplier created: {supplier_name} by {self.request.user}")
            return response
        except Exception as e:
            logger.error(f"Supplier creation failed: {e}", exc_info=True)
            messages.error(self.request, "Failed to add supplier. Please try again.")
            return self.form_invalid(form)


# -------------------- Sales --------------------
@login_required
@role_required(['super_admin', 'hospital_admin', 'pharmacist'])
def sale_create(request):
    prescription = None
    prescription_id = request.GET.get('prescription')
    if prescription_id:
        from prescriptions.models import Prescription
        prescription = get_object_or_404(Prescription, pk=prescription_id)
        # Optionally check if prescription is already fulfilled? Not in model.

    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Lock the sale creation and stock updates
                    sale = form.save(commit=False)
                    sale.pharmacist = request.user
                    sale.save()

                    # Process items
                    medicines = request.POST.getlist('medicine_id[]')
                    quantities = request.POST.getlist('quantity[]')
                    prices = request.POST.getlist('price[]')

                    # Validate stock availability before any changes
                    for i in range(len(medicines)):
                        if medicines[i] and quantities[i] and prices[i]:
                            med = Medicine.objects.select_for_update().get(pk=medicines[i])
                            qty = int(quantities[i])
                            if med.current_stock < qty:
                                raise ValueError(f"Insufficient stock for {med.brand_name}. Available: {med.current_stock}, Required: {qty}")

                    # All stocks sufficient, proceed
                    for i in range(len(medicines)):
                        if medicines[i] and quantities[i] and prices[i]:
                            med = Medicine.objects.select_for_update().get(pk=medicines[i])
                            qty = int(quantities[i])
                            price = Decimal(prices[i])

                            SaleItem.objects.create(
                                sale=sale,
                                medicine=med,
                                quantity=qty,
                                unit_price=price
                            )
                            # Update stock via service
                            update_stock(med, -qty, 'sale', sale.invoice_number, request.user)

                    sale.calculate_total()
                    messages.success(request, 'Sale completed successfully.')
                    logger.info(f"Sale created: {sale.invoice_number} by {request.user}")
                    return redirect('pharmacy:sale_invoice', pk=sale.pk)

            except ValueError as ve:
                messages.error(request, str(ve))
                logger.warning(f"Sale validation error: {ve}")
            except Exception as e:
                logger.error(f"Sale creation failed: {e}", exc_info=True)
                messages.error(request, "Sale failed. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SaleForm(initial={'patient': prescription.patient if prescription else None})

    context = {
        'form': form,
        'prescription': prescription,
    }
    return render(request, 'pharmacy/sale_create.html', context)


@login_required
@role_required(['super_admin', 'hospital_admin', 'pharmacist'])
def sale_invoice(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('patient', 'pharmacist', 'prescription')
                             .prefetch_related('items__medicine'), pk=pk)
    return render(request, 'pharmacy/invoice.html', {'sale': sale})


# -------------------- Reports --------------------
@login_required
@role_required(['super_admin', 'hospital_admin', 'pharmacist'])
def reports(request):
    # Generate sales, purchase, inventory reports
    # For performance, use aggregations and only necessary data.
    context = {}
    return render(request, 'pharmacy/reports.html', context)

class SaleListView(ListView):
    model = Sale
    template_name = "pharmacy/sale_list.html"
    context_object_name = "sales"

class PurchaseListView(ListView):
    model = PurchaseOrder
    template_name = "pharmacy/purchase_list.html"
    context_object_name = "purchases"

def inventory_logs(request):
    return render(request, "pharmacy/inventory_logs.html")

@login_required
@role_required(['super_admin', 'hospital_admin', 'pharmacist'])
def stock_adjustment(request):
    """
    Temporary Stock Adjustment Page
    """
    return render(request, "pharmacy/stock_adjustment.html")