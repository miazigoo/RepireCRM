from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from orders.models import Order
from shops.models import Shop
from users.statistics import employees_statistics_queryset

from .models import GeneratedReport, ReportTemplate
from .services import ReportService

router = Router(tags=["Отчеты"])


def _ensure_aware(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _resolve_period_range(
    period: str = "30_days",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[datetime, datetime, int]:
    end_date = _ensure_aware(date_to) if date_to else timezone.now()

    if date_from:
        start_date = _ensure_aware(date_from)
    elif period == "today":
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "7_days":
        start_date = end_date - timedelta(days=6)
    elif period == "90_days":
        start_date = end_date - timedelta(days=89)
    elif period == "month":
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = end_date - timedelta(days=29)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    days = max((end_date.date() - start_date.date()).days + 1, 1)
    return start_date, end_date, days


def _get_scoped_orders_queryset(
    request,
    shop_id: int | None = None,
    all_shops: bool = False,
):
    queryset = Order.objects.all()
    if all_shops:
        if not request.auth.can_view_global_statistics():
            raise PermissionError("Нет прав для общей статистики по филиалам")
        return queryset

    if shop_id:
        shop = get_object_or_404(Shop, id=shop_id, is_active=True)
        if not request.auth.can_access_shop(shop):
            raise PermissionError("Нет доступа к выбранному филиалу")
        return queryset.filter(shop=shop)

    current_shop = getattr(request, "current_shop", None)
    if current_shop:
        return queryset.filter(shop=current_shop)

    return queryset.filter(shop__in=request.auth.get_available_shops())


def _sum_payable_total(queryset) -> Decimal:
    orders = queryset.prefetch_related(
        "orderservice_set",
        "discounts",
    )
    return sum((order.total_cost for order in orders), Decimal("0.00"))


@router.get("/sla", response=dict)
def get_sla_report(
    request,
    date_from: datetime,
    date_to: datetime,
    shop_id: int | None = None,
    all_shops: bool = False,
):
    """SLA по срокам выполнения заказов"""
    if not request.auth.has_permission("reports.view_dashboard"):
        raise PermissionError("Нет прав для просмотра отчета SLA")

    service = ReportService()
    return service.generate_sla_report(
        date_from=date_from,
        date_to=date_to,
        shop_id=shop_id,
        user=request.auth,
        current_shop=getattr(request, "current_shop", None),
        all_shops=all_shops,
    )


@router.get("/dashboard-metrics", response=dict)
def get_dashboard_metrics(
    request,
    period: str = "30_days",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    shop_id: int | None = None,
    all_shops: bool = False,
):
    """Метрики для дашборда"""
    if not request.auth.has_permission("reports.view_dashboard"):
        raise PermissionError("Нет прав для просмотра дашборда")

    start_date, end_date, days = _resolve_period_range(period, date_from, date_to)
    prev_end_date = start_date - timedelta(microseconds=1)
    prev_start_date = start_date - (end_date - start_date)

    orders_qs = _get_scoped_orders_queryset(
        request, shop_id=shop_id, all_shops=all_shops
    )

    # Текущий период
    current_orders = orders_qs.filter(created_at__range=[start_date, end_date])
    current_completed = current_orders.filter(status="completed")

    # Предыдущий период для сравнения
    prev_orders = orders_qs.filter(created_at__range=[prev_start_date, prev_end_date])
    prev_completed = prev_orders.filter(status="completed")

    # Расчеты
    current_revenue = _sum_payable_total(current_completed)
    prev_revenue = _sum_payable_total(prev_completed)

    # Средний чек
    current_avg_check = (
        current_revenue / current_completed.count()
        if current_completed.count() > 0
        else Decimal("0")
    )

    # Конверсия
    total_current = current_orders.count()
    completed_current = current_completed.count()
    conversion_rate = (
        (completed_current / total_current * 100) if total_current > 0 else 0
    )

    # Топ услуги
    from orders.models import OrderService

    service_revenue = ExpressionWrapper(
        F("price") * F("quantity"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    top_services = (
        OrderService.objects.filter(order__in=current_orders)
        .values("service__name")
        .annotate(total_count=Count("id"), total_revenue=Sum(service_revenue))
        .order_by("-total_revenue")[:5]
    )

    # Статистика по техникам
    technician_stats = (
        orders_qs.filter(
            assigned_to__isnull=False,
            status="completed",
            completed_at__range=[start_date, end_date],
        )
        .values("assigned_to__first_name", "assigned_to__last_name")
        .annotate(
            completed_orders=Count("id"),
            total_revenue=Sum("final_cost"),
        )
        .order_by("-completed_orders")
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days,
        },
        "revenue": {
            "current": float(current_revenue),
            "previous": float(prev_revenue),
            "growth_percent": float(
                ((current_revenue - prev_revenue) / prev_revenue * 100)
                if prev_revenue > 0
                else 0
            ),
        },
        "orders": {
            "total": total_current,
            "completed": completed_current,
            "in_progress": total_current - completed_current,
            "conversion_rate": round(conversion_rate, 2),
        },
        "avg_check": {
            "current": float(current_avg_check),
        },
        "top_services": [
            {
                "name": item["service__name"],
                "count": item["total_count"],
                "revenue": float(item["total_revenue"] or 0),
            }
            for item in top_services
        ],
        "technician_performance": [
            {
                "name": (
                    f"{item['assigned_to__first_name']} "
                    f"{item['assigned_to__last_name']}"
                ),
                "completed_orders": item["completed_orders"],
                "revenue": float(item["total_revenue"] or 0),
            }
            for item in technician_stats
        ],
    }


@router.get("/financial", response=dict)
def get_financial_report(
    request,
    date_from: datetime,
    date_to: datetime,
    shop_id: int | None = None,
    all_shops: bool = False,
):
    """Финансовый отчет"""
    if not request.auth.has_permission("reports.view_financial"):
        raise PermissionError("Нет прав для просмотра финансовых отчетов")

    report_service = ReportService()
    return report_service.generate_financial_report(
        date_from=date_from,
        date_to=date_to,
        shop_id=shop_id,
        user=request.auth,
        current_shop=getattr(request, "current_shop", None),
        all_shops=all_shops,
    )


@router.get("/employees", response=dict)
def get_employees_report(
    request,
    period: str = "month",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    shop_id: int | None = None,
    all_shops: bool = False,
):
    """Статистика по сотрудникам: заказы, услуги, продажи, задачи и оплата."""
    if not request.auth.has_permission("reports.view_dashboard"):
        raise PermissionError("Нет прав для просмотра отчетов по сотрудникам")

    start_date, end_date, _days = _resolve_period_range(period, date_from, date_to)
    if all_shops:
        if not request.auth.can_view_global_statistics():
            raise PermissionError("Нет прав для общей статистики по филиалам")
        shops = None
    elif shop_id:
        shop = get_object_or_404(Shop, id=shop_id, is_active=True)
        if not request.auth.can_access_shop(shop):
            raise PermissionError("Нет доступа к выбранному филиалу")
        shops = Shop.objects.filter(id=shop.id)
    elif getattr(request, "current_shop", None) is not None:
        shops = Shop.objects.filter(id=request.current_shop.id)
    else:
        shops = request.auth.get_available_shops()

    return {
        "period": {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
        },
        "items": employees_statistics_queryset(
            request.auth,
            start_date,
            end_date,
            shops=shops,
        ),
    }


@router.get("/inventory-turnover", response=dict)
def get_inventory_turnover(request, period_days: int = 30):
    """Отчет по оборачиваемости склада"""
    if not request.auth.has_permission("inventory.view_reports"):
        raise PermissionError("Нет прав для просмотра складских отчетов")

    from inventory.services import InventoryReportService

    service = InventoryReportService()
    return service.get_turnover_report(
        period_days, request.auth, current_shop=getattr(request, "current_shop", None)
    )


@router.post("/generate/{template_id}", response=dict)
def generate_report(request, template_id: int, parameters: dict = None):
    """Генерация отчета по шаблону"""
    template = get_object_or_404(ReportTemplate, id=template_id)

    # Проверяем права
    if not request.auth.has_permission("reports.generate_reports"):
        raise PermissionError("Нет прав для генерации отчетов")

    report_service = ReportService()
    report = report_service.generate_report(
        template=template, parameters=parameters or {}, user=request.auth
    )

    return {
        "report_id": report.id,
        "data": report.data,
        "summary": report.summary,
        "charts_config": report.charts_config,
    }


@router.get("/export/dashboard")
def export_dashboard_report(
    request,
    period: str = "30_days",
    format: str = "pdf",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    shop_id: int | None = None,
    all_shops: bool = False,
):
    """Экспорт текущего дашборда без предварительно созданного GeneratedReport."""
    if not request.auth.has_permission("reports.export_reports"):
        raise PermissionError("Нет прав для экспорта отчетов")

    metrics = get_dashboard_metrics(
        request,
        period=period,
        date_from=date_from,
        date_to=date_to,
        shop_id=shop_id,
        all_shops=all_shops,
    )
    filename = f"dashboard-report-{period}"

    if format == "excel":
        rows = [
            "Показатель;Значение",
            f"Выручка;{metrics['revenue']['current']}",
            f"Заказов;{metrics['orders']['total']}",
            f"Завершено;{metrics['orders']['completed']}",
            f"Средний чек;{metrics['avg_check']['current']}",
        ]
        response = HttpResponse(
            "\n".join(rows),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    if format != "pdf":
        return HttpResponse("Unsupported format", status=400)

    body = (
        "Repair CRM dashboard report\n"
        f"Period: {period}\n"
        f"Revenue: {metrics['revenue']['current']}\n"
        f"Orders: {metrics['orders']['total']}\n"
        f"Completed: {metrics['orders']['completed']}\n"
        f"Average check: {metrics['avg_check']['current']}\n"
    )
    response = HttpResponse(body, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response


@router.get("/export/{report_id}")
def export_report(request, report_id: int, format: str = "pdf"):
    """Экспорт отчета в файл"""
    report = get_object_or_404(GeneratedReport, id=report_id)

    if not request.auth.has_permission("reports.export_reports"):
        raise PermissionError("Нет prав для экспорта отчетов")

    from .exporters import ReportExporter

    exporter = ReportExporter()

    if format == "pdf":
        return exporter.export_pdf(report)
    elif format == "excel":
        return exporter.export_excel(report)
    else:
        return {"error": "Unsupported format"}
