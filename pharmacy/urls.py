from django.urls import path
from . import views

app_name = 'pharmacy'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Medicine
    path('medicines/', views.MedicineListView.as_view(), name='medicine_list'),
    path('medicines/create/', views.MedicineCreateView.as_view(), name='medicine_create'),
    path('medicines/<int:pk>/', views.MedicineDetailView.as_view(), name='medicine_detail'),
    path('medicines/<int:pk>/edit/', views.MedicineUpdateView.as_view(), name='medicine_edit'),
    path('medicines/<int:pk>/delete/', views.MedicineDeleteView.as_view(), name='medicine_delete'),

    # Inventory
    path('inventory/', views.inventory_view, name='inventory'),
    path('inventory/logs/', views.inventory_logs, name='inventory_logs'),
    path('inventory/stock-adjustment/', views.stock_adjustment, name='stock_adjustment'),

    # Suppliers
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),

    # Sales
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/create/', views.sale_create, name='sale_create'),
    path('sales/invoice/<int:pk>/', views.sale_invoice, name='sale_invoice'),

    # Purchases
    path('purchases/', views.PurchaseListView.as_view(), name='purchase_list'),

    # Reports
    path('reports/', views.reports, name='reports'),
]