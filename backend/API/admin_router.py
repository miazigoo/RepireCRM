from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema

from orders.models import Order
from shops.models import Shop
from users.models import Permission, Role

router = Router(tags=["Администрирование"])


class AdminPermissionSchema(Schema):
    id: int
    name: str
    code: str
    codename: str
    category: str
    description: str = ""

    @staticmethod
    def resolve_code(obj):
        return obj.codename


class AdminRoleSchema(Schema):
    id: int
    name: str
    code: str
    description: str = ""
    permissions_count: int = 0
    permissions: list[AdminPermissionSchema] = []

    @staticmethod
    def resolve_permissions_count(obj):
        return obj.permissions.count()

    @staticmethod
    def resolve_permissions(obj):
        return obj.permissions.all()


class AdminShopSchema(Schema):
    id: int
    name: str
    code: str
    address: str = ""
    phone: str = ""
    email: str = ""
    is_active: bool
    timezone: str
    currency: str


class AdminUserSchema(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    middle_name: str = ""
    email: str = ""
    phone: str = ""
    is_director: bool
    is_active: bool
    current_shop: AdminShopSchema | None = None
    role: AdminRoleSchema | None = None
    shops: list[AdminShopSchema] = []
    last_login: str | None = None

    @staticmethod
    def resolve_phone(obj):
        return str(obj.phone or "")

    @staticmethod
    def resolve_shops(obj):
        return obj.shops.all()

    @staticmethod
    def resolve_last_login(obj):
        return obj.last_login.isoformat() if obj.last_login else None


class UserCreateSchema(Schema):
    username: str
    password: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    email: str = ""
    phone: str | None = None
    role_id: int | None = None
    shop_ids: list[int] = []
    is_director: bool = False


class UserUpdateSchema(Schema):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role_id: int | None = None
    shop_ids: list[int] | None = None
    is_director: bool | None = None
    is_active: bool | None = None


class PasswordResetSchema(Schema):
    password: str


class ShopCreateSchema(Schema):
    name: str
    code: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str = "Europe/Moscow"
    currency: str = "RUB"
    is_active: bool = True


class ShopUpdateSchema(Schema):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str | None = None
    currency: str | None = None
    is_active: bool | None = None


class RoleCreateSchema(Schema):
    name: str
    code: str
    description: str | None = None
    permission_ids: list[int] = []


class RoleUpdateSchema(Schema):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    permission_ids: list[int] | None = None


def _ensure_admin(request):
    if not (request.auth.is_superuser or request.auth.is_director):
        raise PermissionError("Нет прав для администрирования")


def _sync_user_shops(user, shop_ids):
    shops = Shop.objects.filter(id__in=shop_ids)
    user.shops.set(shops)
    if user.current_shop_id not in set(shops.values_list("id", flat=True)):
        user.current_shop = shops.first()
        user.save(update_fields=["current_shop"])


@router.get("/users", response=list[AdminUserSchema])
def list_users(request, page: int = 1, page_size: int = 20):
    _ensure_admin(request)
    offset = max(page - 1, 0) * page_size
    return (
        get_user_model()
        .objects.select_related("role", "current_shop")
        .prefetch_related("shops", "role__permissions")
        .order_by("username")[offset : offset + page_size]
    )


@router.post("/users", response={201: AdminUserSchema, 400: dict})
def create_user(request, data: UserCreateSchema):
    _ensure_admin(request)
    User = get_user_model()
    if User.objects.filter(username=data.username).exists():
        return 400, {"error": "Пользователь с таким логином уже существует"}

    role = Role.objects.filter(id=data.role_id).first() if data.role_id else None
    user = User.objects.create_user(
        username=data.username,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name or "",
        email=data.email or "",
        phone=data.phone or "",
        role=role,
        is_director=data.is_director,
    )
    _sync_user_shops(user, data.shop_ids)
    return 201, user


@router.get("/users/{user_id}", response=AdminUserSchema)
def get_user(request, user_id: int):
    _ensure_admin(request)
    return get_object_or_404(
        get_user_model()
        .objects.select_related("role", "current_shop")
        .prefetch_related("shops", "role__permissions"),
        id=user_id,
    )


@router.put("/users/{user_id}", response=AdminUserSchema)
def update_user(request, user_id: int, data: UserUpdateSchema):
    _ensure_admin(request)
    user = get_object_or_404(get_user_model(), id=user_id)
    incoming = data.dict(exclude_unset=True)
    shop_ids = incoming.pop("shop_ids", None)
    role_id = incoming.pop("role_id", None)
    if role_id is not None:
        user.role = Role.objects.filter(id=role_id).first()
    for field, value in incoming.items():
        if value is not None:
            setattr(user, field, value)
    user.save()
    if shop_ids is not None:
        _sync_user_shops(user, shop_ids)
    return get_user(request, user.id)


@router.delete("/users/{user_id}", response=dict)
def delete_user(request, user_id: int):
    _ensure_admin(request)
    user = get_object_or_404(get_user_model(), id=user_id)
    if user.id == request.auth.id:
        return {"error": "Нельзя удалить текущего пользователя"}
    user.delete()
    return {"success": True}


@router.post("/users/{user_id}/reset-password", response=dict)
def reset_user_password(request, user_id: int, data: PasswordResetSchema):
    _ensure_admin(request)
    user = get_object_or_404(get_user_model(), id=user_id)
    user.set_password(data.password)
    user.save(update_fields=["password"])
    return {"success": True}


@router.get("/shops", response=list[AdminShopSchema])
def list_admin_shops(request):
    _ensure_admin(request)
    return Shop.objects.all().order_by("name")


@router.post("/shops", response={201: AdminShopSchema, 400: dict})
def create_shop(request, data: ShopCreateSchema):
    _ensure_admin(request)
    if Shop.objects.filter(code=data.code).exists():
        return 400, {"error": "Филиал с таким кодом уже существует"}
    shop = Shop.objects.create(**data.dict())
    return 201, shop


@router.get("/shops/{shop_id}", response=AdminShopSchema)
def get_admin_shop(request, shop_id: int):
    _ensure_admin(request)
    return get_object_or_404(Shop, id=shop_id)


@router.put("/shops/{shop_id}", response=AdminShopSchema)
def update_shop(request, shop_id: int, data: ShopUpdateSchema):
    _ensure_admin(request)
    shop = get_object_or_404(Shop, id=shop_id)
    for field, value in data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(shop, field, value)
    shop.save()
    return shop


@router.delete("/shops/{shop_id}", response=dict)
def delete_shop(request, shop_id: int):
    _ensure_admin(request)
    shop = get_object_or_404(Shop, id=shop_id)
    shop.is_active = False
    shop.save(update_fields=["is_active"])
    return {"success": True}


@router.get("/roles", response=list[AdminRoleSchema])
def list_roles(request):
    _ensure_admin(request)
    return Role.objects.prefetch_related("permissions").order_by("name")


@router.post("/roles", response={201: AdminRoleSchema, 400: dict})
def create_role(request, data: RoleCreateSchema):
    _ensure_admin(request)
    if Role.objects.filter(code=data.code).exists():
        return 400, {"error": "Роль с таким кодом уже существует"}
    role = Role.objects.create(
        name=data.name,
        code=data.code,
        description=data.description or "",
    )
    role.permissions.set(Permission.objects.filter(id__in=data.permission_ids))
    return 201, role


@router.get("/roles/{role_id}", response=AdminRoleSchema)
def get_role(request, role_id: int):
    _ensure_admin(request)
    return get_object_or_404(Role.objects.prefetch_related("permissions"), id=role_id)


@router.put("/roles/{role_id}", response=AdminRoleSchema)
def update_role(request, role_id: int, data: RoleUpdateSchema):
    _ensure_admin(request)
    role = get_object_or_404(Role, id=role_id)
    incoming = data.dict(exclude_unset=True)
    permission_ids = incoming.pop("permission_ids", None)
    for field, value in incoming.items():
        if value is not None:
            setattr(role, field, value)
    role.save()
    if permission_ids is not None:
        role.permissions.set(Permission.objects.filter(id__in=permission_ids))
    return get_role(request, role.id)


@router.delete("/roles/{role_id}", response=dict)
def delete_role(request, role_id: int):
    _ensure_admin(request)
    role = get_object_or_404(Role, id=role_id)
    role.delete()
    return {"success": True}


@router.get("/permissions", response=list[AdminPermissionSchema])
def list_permissions(request):
    _ensure_admin(request)
    return Permission.objects.all().order_by("category", "name")


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
