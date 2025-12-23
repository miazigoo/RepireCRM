from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from customers.models import Customer
from inventory.models import StockMovement
from orders.models import Order, OrderService

from .models import GeneratedReport, ReportTemplate


class ReportService:
    """Сервис генерации отчетов"""

    def generate_financial_report(self, date_from, date_to, shop_id=None, user=None):
        """Генерация финансового отчета"""

        # Базовый queryset
        orders_qs = Order.objects.filter(created_at__range=[date_from, date_to])

        # Фильтрация по магазину
        if shop_id:
            orders_qs = orders_qs.filter(shop_id=shop_id)
        elif not user.is_director:
            available_shops = user.get_available_shops()
            orders_qs = orders_qs.filter(shop__in=available_shops)

        # Основные метрики
        completed_orders = orders_qs.filter(status="completed")

        total_revenue = completed_orders.aggregate(total=Sum("final_cost"))[
            "total"
        ] or Decimal("0")

        total_cost = completed_orders.aggregate(total=Sum("cost_estimate"))[
            "total"
        ] or Decimal("0")

        # Доходы по дням
        daily_revenue = []
        current_date = date_from.date()
        end_date = date_to.date()

        while current_date <= end_date:
            day_revenue = completed_orders.filter(
                completed_at__date=current_date
            ).aggregate(total=Sum("final_cost"))["total"] or Decimal("0")

            daily_revenue.append(
                {"date": current_date.isoformat(), "revenue": float(day_revenue)}
            )
            current_date += timedelta(days=1)

        # Доходы по услугам
        services_revenue = (
            OrderService.objects.filter(order__in=completed_orders)
            .values("service__name")
            .annotate(total_revenue=Sum("total_price"), count=Count("id"))
            .order_by("-total_revenue")
        )

        # Доходы по магазинам
        shops_revenue = (
            completed_orders.values("shop__name")
            .annotate(total_revenue=Sum("final_cost"), orders_count=Count("id"))
            .order_by("-total_revenue")
        )

        return {
            "summary": {
                "total_revenue": float(total_revenue),
                "total_orders": completed_orders.count(),
                "avg_check": float(
                    total_revenue / completed_orders.count()
                    if completed_orders.count() > 0
                    else 0
                ),
                "period_days": (date_to - date_from).days + 1,
            },
            "daily_revenue": daily_revenue,
            "services_breakdown": [
                {
                    "service": item["service__name"],
                    "revenue": float(item["total_revenue"]),
                    "count": item["count"],
                }
                for item in services_revenue
            ],
            "shops_breakdown": [
                {
                    "shop": item["shop__name"],
                    "revenue": float(item["total_revenue"]),
                    "orders": item["orders_count"],
                }
                for item in shops_revenue
            ],
        }

    def generate_performance_report(self, date_from, date_to, user=None):
        """Отчет по производительности техников"""

        orders_qs = Order.objects.filter(
            assigned_to__isnull=False, created_at__range=[date_from, date_to]
        )

        if not user.is_director:
            available_shops = user.get_available_shops()
            orders_qs = orders_qs.filter(shop__in=available_shops)

        # Статистика по техникам
        technicians_stats = orders_qs.values(
            "assigned_to__id", "assigned_to__first_name", "assigned_to__last_name"
        ).annotate(
            total_orders=Count("id"),
            completed_orders=Count("id", filter=Q(status="completed")),
            total_revenue=Sum("final_cost", filter=Q(status="completed")),
            avg_completion_days=Avg(
                models.ExpressionWrapper(
                    models.F("completed_at") - models.F("created_at"),
                    output_field=models.DurationField(),
                ),
                filter=Q(status="completed"),
            ),
        )

        # Конверсия по статусам
        status_stats = (
            orders_qs.values("status").annotate(count=Count("id")).order_by("status")
        )

        return {
            "technicians": [
                {
                    "technician_id": item["assigned_to__id"],
                    "name": f"{item['assigned_to__first_name']} {item['assigned_to__last_name']}",
                    "total_orders": item["total_orders"],
                    "completed_orders": item["completed_orders"],
                    "completion_rate": (
                        item["completed_orders"] / item["total_orders"] * 100
                    )
                    if item["total_orders"] > 0
                    else 0,
                    "total_revenue": float(item["total_revenue"] or 0),
                    "avg_completion_days": item["avg_completion_days"].days
                    if item["avg_completion_days"]
                    else 0,
                }
                for item in technicians_stats
            ],
            "status_distribution": [
                {"status": item["status"], "count": item["count"]}
                for item in status_stats
            ],
        }

    def generate_sla_report(self, date_from, date_to, shop_id=None, user=None):
        """SLA: соблюдение плановых сроков (использует предрасчитанные поля)"""
        qs = Order.objects.filter(completed_at__range=[date_from, date_to])

        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        elif user and not user.is_director:
            qs = qs.filter(shop__in=user.get_available_shops())

        # Только те, где мы можем оценить SLA
        qs = qs.filter(sla_on_time__isnull=False)

        total = qs.count()
        on_time = qs.filter(sla_on_time=True).count()
        late = qs.filter(sla_on_time=False).count()

        # Средние
        avg_delay = qs.filter(sla_delay_minutes__gt=0).aggregate(
            avg=Avg("sla_delay_minutes")
        )["avg"]
        avg_early = qs.filter(sla_delay_minutes__lt=0).aggregate(
            avg=Avg("sla_delay_minutes")
        )["avg"]

        # Разрез по техникам
        by_technician = (
            qs.values("assigned_to__first_name", "assigned_to__last_name")
            .annotate(
                total=Count("id"),
                on_time=Count("id", filter=Q(sla_on_time=True)),
                late=Count("id", filter=Q(sla_on_time=False)),
                avg_delay=Avg("sla_delay_minutes", filter=Q(sla_delay_minutes__gt=0)),
            )
            .order_by("-on_time", "-total")
        )

        # Разрез по типам устройств
        by_device_type = (
            qs.values("device__model__device_type__name")
            .annotate(
                total=Count("id"),
                on_time=Count("id", filter=Q(sla_on_time=True)),
                late=Count("id", filter=Q(sla_on_time=False)),
            )
            .order_by("-total")
        )

        return {
            "summary": {
                "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
                "total": total,
                "on_time": on_time,
                "late": late,
                "sla_rate_percent": round((on_time / total * 100) if total else 0, 2),
                "avg_delay_minutes": int(avg_delay) if avg_delay is not None else 0,
                "avg_early_minutes": abs(int(avg_early))
                if avg_early is not None
                else 0,
            },
            "by_technician": [
                {
                    "name": f"{r['assigned_to__first_name']} {r['assigned_to__last_name']}".strip(),
                    "total": r["total"],
                    "on_time": r["on_time"],
                    "late": r["late"],
                    "avg_delay_minutes": int(r["avg_delay"])
                    if r["avg_delay"] is not None
                    else 0,
                }
                for r in by_technician
            ],
            "by_device_type": [
                {
                    "device_type": r["device__model__device_type__name"],
                    "total": r["total"],
                    "on_time": r["on_time"],
                    "late": r["late"],
                }
                for r in by_device_type
            ],
        }
