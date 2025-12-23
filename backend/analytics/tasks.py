from celery import shared_task
from django.utils import timezone

from .services import AnalyticsService


@shared_task(name="analytics.tasks.save_monthly_snapshots")
def save_monthly_snapshots():
    now = timezone.now()
    year = now.year
    month = now.month
    # Снимки по всем магазинам и суммарно (shop_id=None)
    AnalyticsService.save_monthly_revenue_snapshot(None, year, month)
    from shops.models import Shop

    for shop_id in Shop.objects.filter(is_active=True).values_list("id", flat=True):
        AnalyticsService.save_monthly_revenue_snapshot(shop_id, year, month)
    return {"status": "ok"}
