# laboratory/services.py
"""
Business logic layer for the Laboratory module.

All core operations (create, update, status changes, statistics)
are implemented here to keep views clean and reusable.
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg, F, QuerySet
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import LabOrder, LabOrderItem, LabResult, LaboratoryTest
from prescriptions.models import Prescription
from appointments.models import Appointment
from patients.models import Patient
from doctors.models import Doctor
from hospitals.models import Hospital


def create_lab_order(
    prescription_id: int,
    test_ids: List[int],
    notes: str = "",
    created_by=None,
) -> LabOrder:
    """
    Create a new lab order from a prescription.

    Args:
        prescription_id: ID of the prescription.
        test_ids: List of LaboratoryTest IDs to include in the order.
        notes: Additional notes for the order.
        created_by: User creating the order.

    Returns:
        LabOrder: The created order instance.

    Raises:
        ValidationError: If the prescription is invalid or already has an order.
    """
    from django.db import transaction

    try:
        prescription = Prescription.objects.select_related(
            'appointment', 'patient', 'doctor', 'hospital'
        ).get(
            pk=prescription_id,
            deleted_at__isnull=True
        )
    except Prescription.DoesNotExist:
        raise ValidationError(_('Prescription not found.'))

    # 1. Appointment must be completed
    if prescription.appointment.status != Appointment.Status.COMPLETED:
        raise ValidationError(_('Prescription must be from a completed appointment.'))

    # 2. Check if prescription already has a lab order
    if hasattr(prescription, 'lab_order'):
        raise ValidationError(_('This prescription already has a lab order.'))

    # 3. Validate test IDs exist and are active
    if not test_ids:
        raise ValidationError(_('At least one test must be selected.'))

    tests = LaboratoryTest.objects.filter(
        pk__in=test_ids,
        is_active=True,
        deleted_at__isnull=True
    ).select_related('category')

    if tests.count() != len(set(test_ids)):
        raise ValidationError(_('One or more selected tests are invalid or inactive.'))

    with transaction.atomic():
        # Create the order (order_number is auto-generated in model's save)
        order = LabOrder(
            prescription=prescription,
            appointment=prescription.appointment,
            patient=prescription.patient,
            doctor=prescription.doctor,
            hospital=prescription.hospital,
            status=LabOrder.Status.ORDERED,
            notes=notes,
            created_by=created_by,
        )
        # Save to generate order_number
        order.save()

        # Create order items
        order_items = []
        for test in tests:
            item = LabOrderItem(
                lab_order=order,
                test=test,
                notes="",  # optional per-item notes
            )
            order_items.append(item)
        LabOrderItem.objects.bulk_create(order_items)

        return order


def add_order_item(
    order_id: int,
    test_id: int,
    notes: str = "",
) -> LabOrderItem:
    """
    Add a new test item to an existing lab order.

    Args:
        order_id: ID of the LabOrder.
        test_id: ID of the LaboratoryTest.
        notes: Optional notes for this specific item.

    Returns:
        LabOrderItem: The created item.

    Raises:
        ValidationError: If the order is already completed/cancelled or test invalid.
    """
    try:
        order = LabOrder.objects.get(pk=order_id, deleted_at__isnull=True)
    except LabOrder.DoesNotExist:
        raise ValidationError(_('Lab order not found.'))

    if order.status in (LabOrder.Status.COMPLETED, LabOrder.Status.CANCELLED):
        raise ValidationError(_('Cannot add items to a completed or cancelled order.'))

    try:
        test = LaboratoryTest.objects.get(pk=test_id, is_active=True, deleted_at__isnull=True)
    except LaboratoryTest.DoesNotExist:
        raise ValidationError(_('Test not found or inactive.'))

    # Check for duplicate item (optional)
    if LabOrderItem.objects.filter(lab_order=order, test=test, deleted_at__isnull=True).exists():
        raise ValidationError(_('This test is already in the order.'))

    item = LabOrderItem(
        lab_order=order,
        test=test,
        notes=notes,
    )
    item.save()
    return item


def update_order_status(
    order_id: int,
    new_status: str,
    updated_by=None,
) -> LabOrder:
    """
    Update the status of a lab order.

    Args:
        order_id: ID of the LabOrder.
        new_status: One of LabOrder.Status choices.
        updated_by: User performing the update.

    Returns:
        LabOrder: The updated instance.

    Raises:
        ValidationError: If status transition is not allowed.
    """
    try:
        order = LabOrder.objects.get(pk=order_id, deleted_at__isnull=True)
    except LabOrder.DoesNotExist:
        raise ValidationError(_('Lab order not found.'))

    if order.status == LabOrder.Status.CANCELLED:
        raise ValidationError(_('Cannot change status of a cancelled order.'))

    if order.status == LabOrder.Status.COMPLETED and new_status != LabOrder.Status.COMPLETED:
        raise ValidationError(_('Cannot revert a completed order.'))

    # Validate status choices
    valid_statuses = [choice[0] for choice in LabOrder.Status.choices]
    if new_status not in valid_statuses:
        raise ValidationError(_('Invalid status value.'))

    # Additional logic: if moving to COMPLETED, ensure all items have results?
    # We can add that as a business rule.
    if new_status == LabOrder.Status.COMPLETED:
        items_without_result = LabOrderItem.objects.filter(
            lab_order=order,
            deleted_at__isnull=True
        ).exclude(
            result__isnull=False
        )
        if items_without_result.exists():
            raise ValidationError(_('Cannot complete order until all tests have results.'))

    order.status = new_status
    order.updated_by = updated_by
    order.save()
    return order


def cancel_order(
    order_id: int,
    cancelled_by=None,
) -> LabOrder:
    """
    Cancel a lab order (soft delete is handled by status change).

    Args:
        order_id: ID of the LabOrder.
        cancelled_by: User cancelling the order.

    Returns:
        LabOrder: The updated instance.
    """
    return update_order_status(order_id, LabOrder.Status.CANCELLED, cancelled_by)


def get_order_with_details(order_id: int) -> LabOrder:
    """
    Retrieve a lab order with all related data pre-fetched for detail views.

    Args:
        order_id: ID of the LabOrder.

    Returns:
        LabOrder: The order instance with related data loaded.

    Raises:
        ValidationError: If order not found.
    """
    try:
        order = LabOrder.objects.select_related(
            'prescription',
            'appointment',
            'patient',
            'patient__user',
            'doctor',
            'doctor__user',
            'hospital',
            'created_by',
            'updated_by',
        ).prefetch_related(
            'items',
            'items__test',
            'items__test__category',
            'items__result',
        ).get(pk=order_id, deleted_at__isnull=True)
    except LabOrder.DoesNotExist:
        raise ValidationError(_('Lab order not found.'))
    return order


def get_dashboard_stats(user=None) -> Dict[str, Any]:
    """
    Retrieve statistics for the laboratory dashboard.

    Args:
        user: Optional user for role-based filtering (not implemented yet).

    Returns:
        Dict with counts and summaries.
    """
    # Base queryset (all active orders)
    qs = LabOrder.objects.filter(deleted_at__isnull=True)

    # Role-based filtering could be added later.

    total_orders = qs.count()
    today = timezone.now().date()
    orders_today = qs.filter(ordered_date__date=today).count()

    status_counts = {}
    for status_choice in LabOrder.Status.choices:
        status_code = status_choice[0]
        status_counts[status_code] = qs.filter(status=status_code).count()

    # Additional stats: average tests per order
    avg_tests = (
        LabOrderItem.objects.filter(
            lab_order__in=qs,
            deleted_at__isnull=True
        ).values('lab_order').annotate(
            cnt=Count('id')
        ).aggregate(avg=Sum('cnt') / Count('lab_order'))['avg'] or 0
    )

    # Total revenue from completed orders (sum of test prices)
    from decimal import Decimal
    total_revenue = (
        LabOrderItem.objects.filter(
            lab_order__in=qs.filter(status=LabOrder.Status.COMPLETED),
            deleted_at__isnull=True
        ).aggregate(
            total=Sum('test__price')
        )['total'] or Decimal('0.00')
    )

    return {
        'total_orders': total_orders,
        'orders_today': orders_today,
        'status_counts': status_counts,
        'avg_tests_per_order': round(avg_tests, 1) if avg_tests else 0,
        'total_revenue': total_revenue,
    }


def search_lab_orders(query: str) -> QuerySet[LabOrder]:
    """
    Search lab orders by order number, patient name, doctor name, or prescription number.

    Args:
        query: Search string.

    Returns:
        Queryset of matching LabOrders.
    """
    if not query:
        return LabOrder.objects.none()

    q = Q()
    q |= Q(order_number__icontains=query)
    q |= Q(patient__user__first_name__icontains=query)
    q |= Q(patient__user__last_name__icontains=query)
    q |= Q(doctor__user__first_name__icontains=query)
    q |= Q(doctor__user__last_name__icontains=query)
    q |= Q(prescription__prescription_number__icontains=query)

    return LabOrder.objects.filter(q, deleted_at__isnull=True).select_related(
        'patient', 'doctor', 'hospital', 'prescription'
    ).order_by('-ordered_date')


def filter_lab_orders(
    status: Optional[str] = None,
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    hospital_id: Optional[int] = None,
    date_from: Optional[timezone.datetime] = None,
    date_to: Optional[timezone.datetime] = None,
) -> QuerySet[LabOrder]:
    """
    Apply filters to LabOrder queryset.

    Args:
        status: Filter by order status.
        patient_id: Filter by patient ID.
        doctor_id: Filter by doctor ID.
        hospital_id: Filter by hospital ID.
        date_from: Filter orders created from this date.
        date_to: Filter orders created up to this date.

    Returns:
        Queryset of filtered LabOrders.
    """
    qs = LabOrder.objects.filter(deleted_at__isnull=True)

    if status:
        qs = qs.filter(status=status)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    if hospital_id:
        qs = qs.filter(hospital_id=hospital_id)
    if date_from:
        qs = qs.filter(ordered_date__gte=date_from)
    if date_to:
        qs = qs.filter(ordered_date__lte=date_to)

    return qs.select_related('patient', 'doctor', 'hospital').order_by('-ordered_date')


def upload_lab_result(
    order_item_id: int,
    result: str,
    interpretation: str = "",
    remarks: str = "",
    report_file=None,
    technician=None,
) -> LabResult:
    """
    Upload or update a lab result for a specific order item.

    Args:
        order_item_id: ID of the LabOrderItem.
        result: Result value.
        interpretation: Clinical interpretation.
        remarks: Additional remarks.
        report_file: Uploaded file (optional).
        technician: User who uploaded the result.

    Returns:
        LabResult: The created or updated result.

    Raises:
        ValidationError: If the order is already completed/cancelled.
    """
    try:
        order_item = LabOrderItem.objects.select_related(
            'lab_order'
        ).get(
            pk=order_item_id,
            deleted_at__isnull=True
        )
    except LabOrderItem.DoesNotExist:
        raise ValidationError(_('Order item not found.'))

    # Check if the parent order allows result entry
    order = order_item.lab_order
    if order.status in (LabOrder.Status.COMPLETED, LabOrder.Status.CANCELLED):
        raise ValidationError(_('Cannot upload result for a completed or cancelled order.'))

    # Use get_or_create for result
    lab_result, created = LabResult.objects.get_or_create(
        order_item=order_item,
        defaults={
            'result': result,
            'interpretation': interpretation,
            'remarks': remarks,
            'report_file': report_file,
            'technician': technician,
        }
    )
    if not created:
        # Update existing result
        lab_result.result = result
        lab_result.interpretation = interpretation
        lab_result.remarks = remarks
        if report_file:
            lab_result.report_file = report_file
        if technician:
            lab_result.technician = technician
        lab_result.save()

    return lab_result


def verify_lab_result(
    result_id: int,
    verified_by,
) -> LabResult:
    """
    Mark a lab result as verified by a doctor/pathologist.

    Args:
        result_id: ID of the LabResult.
        verified_by: User verifying the result.

    Returns:
        LabResult: The updated instance.

    Raises:
        ValidationError: If result not found.
    """
    try:
        result = LabResult.objects.get(pk=result_id, deleted_at__isnull=True)
    except LabResult.DoesNotExist:
        raise ValidationError(_('Lab result not found.'))

    if result.verified_by:
        raise ValidationError(_('This result is already verified.'))

    result.verified_by = verified_by
    result.verified_at = timezone.now()
    result.save()
    return result