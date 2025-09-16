from ninja import Router
from ninja.security import HttpBearer
from django.contrib.auth import authenticate
from django.http import JsonResponse
from users.models import User
from Schemas.common import UserSchema, MessageSchema, ErrorSchema
from Schemas.auth.auth import LoginSchema, TokenSchema, ChangePasswordSchema
import jwt
from django.conf import settings
from datetime import datetime, timedelta

router = Router(tags=["Аутентификация"])


@router.post("/login", response={200: TokenSchema, 401: ErrorSchema}, auth=None)
def login(request, credentials: LoginSchema):
    """Вход в систему"""
    user = authenticate(
        username=credentials.username,
        password=credentials.password
    )

    if user is None:
        return 401, {"error": "Неверные учетные данные"}

    if not user.is_active:
        return 401, {"error": "Аккаунт заблокирован"}

    # Создаем JWT токен
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 7 * 24 * 60 * 60,  # 7 дней в секундах
        "user": UserSchema.from_orm(user)
    }


@router.get("/me", response=UserSchema)
def get_current_user(request):
    """Получение информации о текущем пользователе"""
    return request.auth


@router.post("/change-password", response={200: MessageSchema, 400: ErrorSchema})
def change_password(request, data: ChangePasswordSchema):
    """Смена пароля"""
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
        user.save(update_fields=['current_shop', 'last_login_shop'])

        # Обновляем сессию
        request.session['current_shop_id'] = shop.id

        return {"message": f"Переключено на магазин: {shop.name}"}

    except Shop.DoesNotExist:
        return 403, {"error": "Магазин не найден"}