from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django_ratelimit.decorators import ratelimit
from ninja import File, Router, Schema
from ninja.files import UploadedFile

from Schemas.auth.auth import ChangePasswordSchema, LoginSchema, TokenSchema
from Schemas.common import ErrorSchema, MessageSchema, ShopSchema, UserSchema
from users.statistics import employee_statistics, resolve_period_range

User = get_user_model()

router = Router(tags=["Аутентификация"])


class ProfileUpdateSchema(Schema):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    email: str | None = None
    phone: str | None = None
    profile_status: str | None = None
    bio: str | None = None


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

    # Загружаем полные данные пользователя с relational fields
    user = (
        User.objects.select_related("role", "current_shop")
        .prefetch_related("role__permissions", "shops")
        .get(id=user.id)
    )

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 7 * 24 * 60 * 60,
        "user": user,
    }


@router.get("/me", response=UserSchema)
def get_current_user(request):
    """Получение информации о текущем пользователе"""
    user = (
        User.objects.select_related("role", "current_shop")
        .prefetch_related("role__permissions", "shops")
        .get(id=request.auth.id)
    )
    return user


@router.get("/shops", response=list[ShopSchema])
def get_available_shops(request):
    """Магазины, доступные текущему сотруднику для переключения."""
    return request.auth.get_available_shops().order_by("name")


@router.put("/profile", response=UserSchema)
def update_profile(request, data: ProfileUpdateSchema):
    """Обновление публичных данных профиля сотрудника."""
    user = request.auth
    allowed_fields = {
        "first_name",
        "last_name",
        "middle_name",
        "email",
        "phone",
        "profile_status",
        "bio",
    }
    update_fields = []
    for field, value in data.dict(exclude_unset=True).items():
        if field in allowed_fields and value is not None:
            setattr(user, field, value)
            update_fields.append(field)

    if update_fields:
        user.save(update_fields=update_fields + ["updated_at"])

    return (
        User.objects.select_related("role", "current_shop")
        .prefetch_related("role__permissions", "shops")
        .get(id=user.id)
    )


@router.post("/profile/avatar", response=UserSchema)
def update_profile_avatar(request, avatar: UploadedFile = File(...)):
    """Загрузка аватара текущего сотрудника."""
    user = request.auth
    user.avatar.save(avatar.name, avatar, save=True)
    return (
        User.objects.select_related("role", "current_shop")
        .prefetch_related("role__permissions", "shops")
        .get(id=user.id)
    )


@router.get("/profile/statistics", response=dict)
def get_profile_statistics(
    request,
    period: str = "month",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    all_shops: bool = False,
):
    """Личная статистика и расчет примерной зарплаты сотрудника."""
    start_date, end_date = resolve_period_range(period, date_from, date_to)
    if all_shops:
        shops = request.auth.get_available_shops()
    elif getattr(request, "current_shop", None) is not None:
        shops = [request.current_shop]
    else:
        shops = request.auth.get_available_shops()

    return employee_statistics(
        request.auth,
        start_date,
        end_date,
        shops=shops,
    )


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


@router.post("/switch-shop/{shop_id}", response={200: UserSchema, 403: ErrorSchema})
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

        # Возвращаем обновленного пользователя с relational fields
        user = (
            User.objects.select_related("role", "current_shop")
            .prefetch_related("role__permissions", "shops")
            .get(id=user.id)
        )
        return user

    except Shop.DoesNotExist:
        return 403, {"error": "Магазин не найден"}
