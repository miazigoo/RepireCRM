from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.security import HttpBearer

# Подключаем роутеры
from API.auth.router import router as auth_router
from customers.router import router as customers_router
from inventory.router import router as inventory_router
from loyalty.router import router as loyalty_router
from notifications.router import router as notifications_router
from orders.router import router as orders_router
from reports.router import router as reports_router
from tasks.router import router as tasks_router
from users.models import User


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            user = User.objects.get(id=user_id)
            return user
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None


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
            "/api/docs",  # Swagger документация
            "/api/auth/",
            "/api/customers/",
            "/api/orders/",
        ],
    }


@api.get("/health", auth=None)
def health_check(request):
    return {
        "status": "ok",
        "message": "Backend is running",
        "timestamp": datetime.now().isoformat(),
        "debug": settings.DEBUG,
    }


# Обработчики ошибок
@api.exception_handler(PermissionError)
def permission_error_handler(request, exc):
    return JsonResponse(
        {"error": "Недостаточно прав для выполнения операции"}, status=403
    )


@api.exception_handler(ValueError)
def value_error_handler(request, exc):
    return JsonResponse({"error": str(exc)}, status=400)


api.add_router("/auth", auth_router)
api.add_router("/customers", customers_router)
api.add_router("/orders", orders_router)
api.add_router("/loyalty", loyalty_router)

api.add_router("/inventory", inventory_router)
api.add_router("/reports", reports_router)
api.add_router("/tasks", tasks_router)
api.add_router("/notifications", notifications_router)
