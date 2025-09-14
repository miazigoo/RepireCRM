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