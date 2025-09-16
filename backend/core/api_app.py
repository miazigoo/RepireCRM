from ninja import NinjaAPI
from ninja.security import HttpBearer
from django.http import JsonResponse
from django.contrib.auth import authenticate
from users.models import User
import jwt
from django.conf import settings
from datetime import datetime, timedelta


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            user = User.objects.get(id=user_id)
            return user
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None


# Создаем основной API объект
api = NinjaAPI(
    title="Repair CRM API",
    version="1.0.0",
    description="API для системы управления ремонтом устройств",
    auth=AuthBearer()
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
        ]
    }


@api.get("/health", auth=None)
def health_check(request):
    return {
        "status": "ok",
        "message": "Backend is running",
        "timestamp": datetime.now().isoformat(),
        "debug": settings.DEBUG
    }


# Обработчики ошибок
@api.exception_handler(PermissionError)
def permission_error_handler(request, exc):
    return JsonResponse(
        {"error": "Недостаточно прав для выполнения операции"},
        status=403
    )


@api.exception_handler(ValueError)
def value_error_handler(request, exc):
    return JsonResponse(
        {"error": str(exc)},
        status=400
    )