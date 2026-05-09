from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone


def resolve_period_range(
    period: str = "month",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[datetime, datetime]:
    end_date = _ensure_aware(date_to) if date_to else timezone.now()

    if date_from:
        start_date = _ensure_aware(date_from)
    elif period == "today":
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "7_days":
        start_date = end_date - timedelta(days=6)
    elif period == "30_days":
        start_date = end_date - timedelta(days=29)
    elif period == "year":
        start_date = end_date - timedelta(days=364)
    else:
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    return start_date, end_date


def employee_statistics(
    employee,
    date_from: datetime,
    date_to: datetime,
    shops=None,
) -> dict:
    from inventory.models import RetailSale
    from orders.models import Order, OrderService
    from tasks.models import Task

    if shops is not None:
        shop_filter = Q(shop__in=shops)
        sale_shop_filter = Q(shop__in=shops)
    else:
        shop_filter = Q()
        sale_shop_filter = Q()

    assigned_or_created = Q(assigned_to=employee) | Q(
        assigned_to__isnull=True, created_by=employee
    )
    orders = Order.objects.filter(assigned_or_created & shop_filter)
    completed_orders = orders.filter(
        status=Order.StatusChoices.COMPLETED,
        completed_at__range=[date_from, date_to],
    )
    accepted_orders = orders.filter(created_at__range=[date_from, date_to])

    service_revenue_expr = ExpressionWrapper(
        F("price") * F("quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    service_revenue = OrderService.objects.filter(order__in=completed_orders).aggregate(
        total=Sum(service_revenue_expr)
    )["total"] or Decimal("0")
    repair_revenue = completed_orders.aggregate(total=Sum("final_cost"))[
        "total"
    ] or Decimal("0")
    total_order_revenue = repair_revenue + service_revenue

    sales = RetailSale.objects.filter(
        sale_shop_filter,
        cashier=employee,
        status=RetailSale.Status.COMPLETED,
        completed_at__range=[date_from, date_to],
    )
    product_revenue = sales.aggregate(total=Sum("total_amount"))["total"] or Decimal(
        "0"
    )

    task_shops = shops if shops is not None else employee.shops.all()
    tasks = Task.objects.filter(
        Q(assigned_to=employee)
        | Q(completed_by=employee)
        | Q(assignment_type=Task.AssignmentType.SHOP, assigned_shop__in=task_shops),
        created_at__lte=date_to,
    ).distinct()
    completed_tasks = tasks.filter(
        status=Task.Status.COMPLETED,
        completed_at__range=[date_from, date_to],
    )
    paid_tasks_amount = completed_tasks.filter(is_paid=True).aggregate(
        total=Sum("payment_amount")
    )["total"] or Decimal("0")

    raw_fixed_pay = completed_orders.count() * employee.fixed_order_payment
    raw_service_commission = service_revenue * employee.service_commission_percent / 100
    raw_product_commission = product_revenue * employee.product_commission_percent / 100

    if employee.compensation_type == employee.CompensationType.FIXED:
        fixed_pay = raw_fixed_pay
        service_commission = Decimal("0")
        product_commission = Decimal("0")
    elif employee.compensation_type == employee.CompensationType.COMMISSION:
        fixed_pay = Decimal("0")
        service_commission = raw_service_commission
        product_commission = raw_product_commission
    else:
        fixed_pay = raw_fixed_pay
        service_commission = raw_service_commission
        product_commission = raw_product_commission
    estimated_salary = (
        fixed_pay + service_commission + product_commission + paid_tasks_amount
    )

    return {
        "employee_id": employee.id,
        "employee_name": _employee_name(employee),
        "username": employee.username,
        "role": employee.role.name if employee.role else "",
        "period": {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
        "orders": {
            "accepted": accepted_orders.count(),
            "completed": completed_orders.count(),
            "revenue": float(total_order_revenue),
            "repair_revenue": float(repair_revenue),
            "services_revenue": float(service_revenue),
        },
        "sales": {
            "count": sales.count(),
            "revenue": float(product_revenue),
        },
        "tasks": {
            "assigned": tasks.filter(created_at__range=[date_from, date_to]).count(),
            "completed": completed_tasks.count(),
            "paid_amount": float(paid_tasks_amount),
        },
        "compensation": {
            "type": employee.compensation_type,
            "fixed_order_payment": float(employee.fixed_order_payment),
            "service_commission_percent": float(employee.service_commission_percent),
            "product_commission_percent": float(employee.product_commission_percent),
            "fixed_pay": float(fixed_pay),
            "service_commission": float(service_commission),
            "product_commission": float(product_commission),
            "task_pay": float(paid_tasks_amount),
            "estimated_salary": float(estimated_salary),
        },
    }


def employees_statistics_queryset(
    viewer,
    date_from: datetime,
    date_to: datetime,
    shops=None,
) -> list[dict]:
    User = get_user_model()
    queryset = (
        User.objects.select_related("role")
        .prefetch_related("shops")
        .filter(is_active=True)
    )

    if shops is not None:
        queryset = queryset.filter(shops__in=shops).distinct()

    return [
        employee_statistics(employee, date_from, date_to, shops=shops)
        for employee in queryset.order_by("last_name", "first_name", "username")
    ]


def _ensure_aware(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _employee_name(user) -> str:
    name = user.full_name.strip()
    return name or user.username
