from celery import shared_task

from loyalty.services import LoyaltyService


@shared_task(name="loyalty.tasks.expire_points")
def expire_points():
    LoyaltyService.expire_points()
    return {"status": "ok"}
