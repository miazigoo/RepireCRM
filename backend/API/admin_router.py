from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from ninja import Router

from orders.models import Order
from shops.models import Shop

router = Router(tags=["Администрирование"])


@router.get("/statistics", response=dict)
def get_system_statistics(request):
    """Сводные показатели для главной страницы администрирования."""
    if not (
        request.auth.is_superuser
        or request.auth.is_director
        or request.auth.has_permission("users.view_user")
        or request.auth.has_permission("settings.view_shop")
    ):
        raise PermissionError("Нет прав для просмотра системной статистики")

    User = get_user_model()
    today = timezone.localdate()
    orders = Order.objects.filter(created_at__date=today)

    if not request.auth.is_director and not request.auth.has_permission(
        "orders.view_all_shops"
    ):
        orders = orders.filter(shop__in=request.auth.get_available_shops())
    elif getattr(request, "current_shop", None) is not None:
        orders = orders.filter(shop=request.current_shop)

    today_revenue = orders.aggregate(total=Sum("final_cost"))["total"] or 0

    return {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "total_shops": Shop.objects.count(),
        "active_shops": Shop.objects.filter(is_active=True).count(),
        "total_orders_today": orders.count(),
        "total_revenue_today": float(today_revenue),
        "system_health": "good",
    }
