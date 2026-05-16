from datetime import datetime

import jwt
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.security import HttpBearer

from admin_agent.enforcement import enforce_admin_subscription
from admin_agent.router import router as admin_agent_router

# Подключаем роутеры
from API.admin_router import router as admin_router
from API.auth.router import is_token_blacklisted
from API.auth.router import router as auth_router
from client_sync.router import router as client_sync_router
from customers.router import router as customers_router
from documents.router import router as documents_router
from finance.router import router as finance_router
from inventory.router import router as inventory_router
from loyalty.router import router as loyalty_router
from notifications.router import router as notifications_router
from orders.router import router as orders_router
from promotions.router import router as promotions_router
from reports.router import router as reports_router
from shops.field_visit_router import router as field_visit_router
from shops.router import router as shops_router
from tasks.router import router as tasks_router
from users.models import User


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            jti = payload.get("jti")
            if jti and is_token_blacklisted(jti):
                return None
            user_id = payload.get("user_id")
            user = User.objects.get(id=user_id)
            enforce_admin_subscription(request, user)
            self._attach_current_shop(request, user)
            return user
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None

    def _attach_current_shop(self, request, user):
        from shops.models import Shop

        shop_id = request.META.get("HTTP_X_CURRENT_SHOP")
        shop = None
        if shop_id:
            shop = Shop.objects.filter(id=shop_id, is_active=True).first()
            if shop and not user.can_access_shop(shop):
                shop = None

        if shop is None and user.current_shop_id:
            shop = (
                user.current_shop if user.can_access_shop(user.current_shop) else None
            )

        if shop is None:
            shop = user.get_available_shops().first()

        if shop is not None:
            request.current_shop = shop


# Создаем основной API объект
api = NinjaAPI(
    title="Repair CRM API",
    version="1.0.0",
    description="API для системы управления ремонтом устройств",
    auth=AuthBearer(),
)


# Добавляем корневой endpoint для проверки работоспособности
@api.get("/", auth=None)
def api_root(request):
    return {
        "message": "Repair CRM API is working",
        "version": "1.0.0",
        "status": "ok",
        "endpoints": [
            "/api/docs",
            "/api/auth/",
            "/api/customers/",
            "/api/orders/",
        ],
    }


@api.get("/health", auth=None)
def health_check(request):
    """Liveness + readiness probe: checks DB and Redis connectivity."""
    checks: dict[str, str] = {}
    ok = True

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"
        ok = False

    # Redis / cache check
    try:
        cache.set("__health__", 1, timeout=5)
        assert cache.get("__health__") == 1
        checks["cache"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["cache"] = f"error: {exc}"
        ok = False

    status_code = 200 if ok else 503
    return api.create_response(
        request,
        {
            "status": "ok" if ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        },
        status=status_code,
    )


# Обработчики ошибок
@api.exception_handler(PermissionError)
def permission_error_handler(request, exc):
    if getattr(exc, "errno", None):
        return JsonResponse({"error": "Ошибка доступа к файлу"}, status=500)
    message = str(exc) or "Недостаточно прав для выполнения операции"
    return JsonResponse({"error": message}, status=403)


@api.exception_handler(ValueError)
def value_error_handler(request, exc):
    return JsonResponse({"error": str(exc)}, status=400)


api.add_router("/auth", auth_router)
api.add_router("/customers", customers_router)
api.add_router("/documents", documents_router)
api.add_router("/orders", orders_router)
api.add_router("/loyalty", loyalty_router)
api.add_router("/inventory", inventory_router)
api.add_router("/reports", reports_router)
api.add_router("/tasks", tasks_router)
api.add_router("/notifications", notifications_router)
api.add_router("/shops", shops_router)
api.add_router("", field_visit_router)
api.add_router("/finance", finance_router)
api.add_router("/client-sync", client_sync_router)
api.add_router("/promotions", promotions_router)
api.add_router("/admin", admin_router)
api.add_router("/admin-agent", admin_agent_router)
