from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.db import models
from django.db.models import Count, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from orders.models import Order, OrderService

from .models import AnalyticsPeriod, PopularServiceSnapshot, RevenueSnapshot


class AnalyticsService:
    @staticmethod
    def get_monthly_revenue(shop_id: Optional[int], year: int, month: int) -> dict:
        qs = Order.objects.filter(
            status="completed",
            completed_at__year=year,
            completed_at__month=month,
        )
        if shop_id:
            qs = qs.filter(shop_id=shop_id)

        revenue = qs.aggregate(total=Coalesce(Sum("final_cost"), Decimal("0")))["total"]
        orders = qs.count()
        avg = (revenue / orders) if orders > 0 else Decimal("0")

        # Дополнительная аналитика: услуги/доп.работы
        services_revenue = (
            OrderService.objects.filter(order__in=qs)
            .annotate(
                total=models.ExpressionWrapper(
                    F("price") * F("quantity"),
                    output_field=models.DecimalField(max_digits=12, decimal_places=2),
                )
            )
            .aggregate(total=Coalesce(Sum("total"), Decimal("0")))["total"]
        )

        return {
            "shop_id": shop_id,
            "year": year,
            "month": month,
            "orders": orders,
            "revenue": float(revenue),
            "services_revenue": float(services_revenue or 0),
            "avg_order_value": float(avg),
        }

    @staticmethod
    def get_popular_services(
        shop_id: Optional[int] = None,
        date_from=None,
        date_to=None,
        limit: int = 10,
    ):
        qs = OrderService.objects.select_related("service", "order").filter(
            order__status="completed"
        )

        if shop_id:
            qs = qs.filter(order__shop_id=shop_id)
        if date_from:
            qs = qs.filter(order__completed_at__gte=date_from)
        if date_to:
            qs = qs.filter(order__completed_at__lte=date_to)

        agg = (
            qs.values("service__id", "service__name", "service__category")
            .annotate(
                count=Count("id"),
                revenue=models.ExpressionWrapper(
                    Sum(F("price") * F("quantity")),
                    output_field=models.DecimalField(max_digits=12, decimal_places=2),
                ),
            )
            .order_by("-revenue", "-count")[:limit]
        )

        return [
            {
                "service_id": row["service__id"],
                "name": row["service__name"],
                "category": row["service__category"],
                "count": row["count"],
                "revenue": float(row["revenue"] or 0),
            }
            for row in agg
        ]

    @staticmethod
    def save_monthly_revenue_snapshot(shop_id: Optional[int], year: int, month: int):
        """Сохранить снепшот выручки за месяц"""
        from calendar import monthrange

        data = AnalyticsService.get_monthly_revenue(shop_id, year, month)
        shop = None
        if shop_id:
            from shops.models import Shop

            shop = Shop.objects.get(id=shop_id)

        start = datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
        end = datetime(
            year,
            month,
            monthrange(year, month)[1],
            23,
            59,
            59,
            tzinfo=timezone.get_current_timezone(),
        )

        obj, _ = RevenueSnapshot.objects.update_or_create(
            period_type=AnalyticsPeriod.MONTH,
            period_start=start,
            period_end=end,
            shop=shop,
            defaults=dict(
                orders=data["orders"],
                revenue=data["revenue"],
                services_revenue=data["services_revenue"],
                avg_order_value=data["avg_order_value"],
            ),
        )
        return obj

    @staticmethod
    def save_popular_services_snapshot(
        shop_id: Optional[int], date_from, date_to, limit: int = 10
    ):
        """Сохранить снепшот топ услуг за произвольный период (тип custom)"""
        items = AnalyticsService.get_popular_services(
            shop_id, date_from, date_to, limit
        )
        shop = None
        if shop_id:
            from shops.models import Shop

            shop = Shop.objects.get(id=shop_id)

        # Чистим старые записи на этот период/магазин
        PopularServiceSnapshot.objects.filter(
            period_type=AnalyticsPeriod.CUSTOM,
            period_start=date_from,
            period_end=date_to,
            shop=shop,
        ).delete()

        bulk = []
        for row in items:
            bulk.append(
                PopularServiceSnapshot(
                    period_type=AnalyticsPeriod.CUSTOM,
                    period_start=date_from,
                    period_end=date_to,
                    shop=shop,
                    service_id=row["service_id"],
                    service_name=row["name"],
                    service_category=row["category"],
                    count=row["count"],
                    revenue=row["revenue"],
                )
            )
        if bulk:
            PopularServiceSnapshot.objects.bulk_create(bulk)

        return len(bulk)
