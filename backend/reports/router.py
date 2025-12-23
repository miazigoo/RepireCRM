from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import paginate

from customers.models import Customer
from orders.models import Order

from .models import GeneratedReport, ReportTemplate
from .services import ReportService

router = Router(tags=["Отчеты"])


@router.get("/sla", response=dict)
def get_sla_report(
    request, date_from: datetime, date_to: datetime, shop_id: Optional[int] = None
):
    """SLA по срокам выполнения заказов"""
    if not request.auth.has_permission("reports.view_dashboard"):
        raise PermissionError("Нет прав для просмотра отчета SLA")

    service = ReportService()
    return service.generate_sla_report(
        date_from=date_from, date_to=date_to, shop_id=shop_id, user=request.auth
    )


@router.get("/dashboard-metrics", response=dict)
def get_dashboard_metrics(request):
    """Метрики для дашборда"""
    if not request.auth.has_permission("reports.view_dashboard"):
        raise PermissionError("Нет прав для просмотра дашборда")

    # Определяем период - последние 30 дней
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    prev_start_date = start_date - timedelta(days=30)

    # Базовый queryset с учетом прав доступа
    orders_qs = Order.objects.all()
    if not request.auth.is_director:
        available_shops = request.auth.get_available_shops()
        orders_qs = orders_qs.filter(shop__in=available_shops)

    # Текущий период
    current_orders = orders_qs.filter(created_at__range=[start_date, end_date])
    current_completed = current_orders.filter(status="completed")

    # Предыдущий период для сравнения
    prev_orders = orders_qs.filter(created_at__range=[prev_start_date, start_date])
    prev_completed = prev_orders.filter(status="completed")

    # Расчеты
    current_revenue = current_completed.aggregate(total=Sum("final_cost"))[
        "total"
    ] or Decimal("0")

    prev_revenue = prev_completed.aggregate(total=Sum("final_cost"))[
        "total"
    ] or Decimal("0")

    # Средний чек
    current_avg_check = current_completed.aggregate(avg=Avg("final_cost"))[
        "avg"
    ] or Decimal("0")

    # Конверсия
    total_current = current_orders.count()
    completed_current = current_completed.count()
    conversion_rate = (
        (completed_current / total_current * 100) if total_current > 0 else 0
    )

    # Топ услуги
    from orders.models import OrderService

    top_services = (
        OrderService.objects.filter(order__created_at__range=[start_date, end_date])
        .values("service__name")
        .annotate(total_count=Count("id"), total_revenue=Sum("total_price"))
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
            avg_completion_time=Avg("completed_at"),  # Нужно будет пересчитать
        )
        .order_by("-completed_orders")
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": 30,
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
                "revenue": float(item["total_revenue"]),
            }
            for item in top_services
        ],
        "technician_performance": [
            {
                "name": f"{item['assigned_to__first_name']} {item['assigned_to__last_name']}",
                "completed_orders": item["completed_orders"],
                "revenue": float(item["total_revenue"] or 0),
            }
            for item in technician_stats
        ],
    }


@router.get("/financial", response=dict)
def get_financial_report(
    request, date_from: datetime, date_to: datetime, shop_id: Optional[int] = None
):
    """Финансовый отчет"""
    if not request.auth.has_permission("reports.view_financial"):
        raise PermissionError("Нет прав для просмотра финансовых отчетов")

    report_service = ReportService()
    return report_service.generate_financial_report(
        date_from=date_from, date_to=date_to, shop_id=shop_id, user=request.auth
    )


@router.get("/inventory-turnover", response=dict)
def get_inventory_turnover(request, period_days: int = 30):
    """Отчет по оборачиваемости склада"""
    if not request.auth.has_permission("inventory.view_reports"):
        raise PermissionError("Нет прав для просмотра складских отчетов")

    from inventory.services import InventoryReportService

    service = InventoryReportService()
    return service.get_turnover_report(period_days, request.auth)


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
