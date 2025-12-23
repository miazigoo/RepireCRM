from typing import List

from django.utils import timezone
from ninja import Router

from .models import Notification
from .notifications_schemas import NotificationSchema
from .services import notification_service

router = Router(tags=["Уведомления"])


@router.get("/", response=List[NotificationSchema])
def get_notifications(request, page: int = 1, limit: int = 20):
    """Получить уведомления пользователя"""
    notifications = Notification.objects.filter(
        recipient=request.auth, is_read=False
    ).order_by("-created_at")[:limit]
    return notifications


@router.post("/{notification_id}/mark-read")
def mark_notification_read(request, notification_id: int):
    """Отметить уведомление как прочитанное"""
    try:
        notification = Notification.objects.get(
            id=notification_id, recipient=request.auth
        )
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return {"success": True}
    except Notification.DoesNotExist:
        return {"error": "Уведомление не найдено"}
