from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from ninja import Router
from ninja.security import HttpBearer

from Schemas.auth.auth import ChangePasswordSchema, LoginSchema, TokenSchema
from Schemas.common import ErrorSchema, MessageSchema, UserSchema
from users.models import User

router = Router(tags=["Аутентификация"])


@ratelimit(key="ip", rate="5/m", block=True)
@router.post("/login", response={200: TokenSchema, 401: ErrorSchema}, auth=None)
def login(request, credentials: LoginSchema):
    """Вход в систему"""
    user = authenticate(username=credentials.username, password=credentials.password)

    if user is None:
        return 401, {"error": "Неверные учетные данные"}

    if not user.is_active:
        return 401, {"error": "Аккаунт заблокирован"}

    # Создаем JWT токен
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 7 * 24 * 60 * 60,
        "user": UserSchema.from_orm(user) if hasattr(UserSchema, "from_orm") else user,
    }


@router.get("/me", response=UserSchema)
def get_current_user(request):
    """Получение информации о текущем пользователе"""
    return request.auth


@router.post("/change-password", response={200: MessageSchema, 400: ErrorSchema})
def change_password(request, data: ChangePasswordSchema):
    """Смена пароля"""
    try:
        data.validate()
    except ValueError as e:
        return 400, {"error": str(e)}
    user = request.auth

    if not user.check_password(data.old_password):
        return 400, {"error": "Неверный текущий пароль"}

    user.set_password(data.new_password)
    user.save()

    return {"message": "Пароль успешно изменен"}


@router.post("/switch-shop/{shop_id}", response={200: MessageSchema, 403: ErrorSchema})
def switch_shop(request, shop_id: int):
    """Переключение между магазинами"""
    user = request.auth

    try:
        from shops.models import Shop

        shop = Shop.objects.get(id=shop_id, is_active=True)

        if not user.can_access_shop(shop):
            return 403, {"error": "Нет доступа к данному магазину"}

        user.current_shop = shop
        user.last_login_shop = shop
        user.save(update_fields=["current_shop", "last_login_shop"])

        # Обновляем сессию
        request.session["current_shop_id"] = shop.id

        return {"message": f"Переключено на магазин: {shop.name}"}

    except Shop.DoesNotExist:
        return 403, {"error": "Магазин не найден"}
