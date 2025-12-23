from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class AnalyticsPeriod(models.TextChoices):
    DAY = "day", "День"
    WEEK = "week", "Неделя"
    MONTH = "month", "Месяц"
    YEAR = "year", "Год"
    CUSTOM = "custom", "Произвольный период"


class RevenueSnapshot(models.Model):
    """
    Снепшот выручки/заказов за период.
    Используется для быстрых дашбордов, не дергая тяжелые агрегаты.
    """

    period_type = models.CharField(max_length=10, choices=AnalyticsPeriod.choices)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, null=True, blank=True
    )

    orders = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    services_revenue = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0")
    )
    avg_order_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Снепшот выручки"
        verbose_name_plural = "Снепшоты выручки"
        unique_together = ("period_type", "period_start", "period_end", "shop")
        indexes = [
            models.Index(fields=["period_type", "period_start"]),
            models.Index(fields=["shop", "period_type"]),
        ]


class PopularServiceSnapshot(models.Model):
    """
    Топ услуг за период (по выручке/количеству).
    """

    period_type = models.CharField(max_length=10, choices=AnalyticsPeriod.choices)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, null=True, blank=True
    )

    service_id = models.IntegerField()
    service_name = models.CharField(max_length=200)
    service_category = models.CharField(max_length=50)

    count = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Снепшот популярных услуг"
        verbose_name_plural = "Снепшоты популярных услуг"
        unique_together = (
            "period_type",
            "period_start",
            "period_end",
            "shop",
            "service_id",
        )
        indexes = [
            models.Index(fields=["period_type", "period_start"]),
            models.Index(fields=["shop"]),
            models.Index(fields=["revenue"]),
        ]


class TechnicianPerformanceSnapshot(models.Model):
    """
    Эффективность техников за период (кол-во, выручка, среднее время)
    """

    period_type = models.CharField(max_length=10, choices=AnalyticsPeriod.choices)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, null=True, blank=True
    )

    technician = models.ForeignKey(User, on_delete=models.CASCADE)
    completed_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0")
    )
    avg_completion_days = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0")
    )

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Снепшот эффективности техников"
        verbose_name_plural = "Снепшоты эффективности техников"
        unique_together = (
            "period_type",
            "period_start",
            "period_end",
            "shop",
            "technician",
        )
        indexes = [
            models.Index(fields=["period_type", "period_start"]),
            models.Index(fields=["shop", "technician"]),
        ]


class DeviceTypeStatsSnapshot(models.Model):
    """
    Статистика по типам устройств за период (на какие типы больше заказов/выручки)
    """

    period_type = models.CharField(max_length=10, choices=AnalyticsPeriod.choices)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, null=True, blank=True
    )

    device_type_name = models.CharField(max_length=100)
    orders = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Снепшот по типам устройств"
        verbose_name_plural = "Снепшоты по типам устройств"
        unique_together = (
            "period_type",
            "period_start",
            "period_end",
            "shop",
            "device_type_name",
        )
        indexes = [
            models.Index(fields=["period_type", "period_start"]),
            models.Index(fields=["shop"]),
        ]
