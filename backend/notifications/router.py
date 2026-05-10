from django.db.models import Q
from django.utils import timezone
from ninja import Router

from .models import Notification
from .notifications_schemas import NotificationSchema

router = Router(tags=["Уведомления"])


def _accessible_notifications(request):
    filters = Q(recipient=request.auth)

    current_shop = getattr(request, "current_shop", None)
    if current_shop:
        filters |= Q(shop=current_shop)

    role = getattr(request.auth, "role", None)
    if role:
        filters |= Q(role_code=role.code)

    return (
        Notification.objects.select_related("notification_type")
        .filter(filters)
        .distinct()
    )


@router.get("/", response=list[NotificationSchema])
def get_notifications(
    request, page: int = 1, limit: int = 20, unread_only: bool = True
):
    """Получить уведомления пользователя"""
    limit = max(1, min(limit, 50))
    page = max(1, page)
    offset = (page - 1) * limit

    notifications = _accessible_notifications(request)
    if unread_only:
        notifications = notifications.filter(is_read=False)

    return notifications.order_by("-created_at")[offset : offset + limit]


@router.post("/{notification_id}/mark-read")
def mark_notification_read(request, notification_id: int):
    """Отметить уведомление как прочитанное"""
    notification = _accessible_notifications(request).filter(id=notification_id).first()
    if not notification:
        return {"error": "Уведомление не найдено"}

    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at"])
    return {"success": True}


@router.post("/mark-all-read")
def mark_all_notifications_read(request):
    """Отметить все доступные уведомления как прочитанные"""
    updated = (
        _accessible_notifications(request)
        .filter(is_read=False)
        .update(
            is_read=True,
            read_at=timezone.now(),
        )
    )
    return {"success": True, "updated": updated}
