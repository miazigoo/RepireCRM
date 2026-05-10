from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema

from orders.models import Order
from shops.models import Shop
from users.models import Permission, Role
from users.permissions import CATEGORY_LABELS
from users.statistics import employees_statistics_queryset, resolve_period_range

router = Router(tags=["Администрирование"])


class AdminPermissionSchema(Schema):
    id: int
    name: str
    code: str
    codename: str
    category: str
    category_label: str = ""
    description: str = ""

    @staticmethod
    def resolve_code(obj):
        return obj.codename

    @staticmethod
    def resolve_category_label(obj):
        return CATEGORY_LABELS.get(obj.category, obj.category)


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
    city: str = ""
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
    can_field_visit: bool = False
    is_active: bool
    current_shop: AdminShopSchema | None = None
    avatar: str | None = None
    profile_status: str = ""
    bio: str = ""
    compensation_type: str = "fixed"
    fixed_order_payment: float = 0
    service_commission_percent: float = 0
    product_commission_percent: float = 0
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

    @staticmethod
    def resolve_avatar(obj):
        return obj.avatar.url if obj.avatar else None

    @staticmethod
    def resolve_fixed_order_payment(obj):
        return float(obj.fixed_order_payment or 0)

    @staticmethod
    def resolve_service_commission_percent(obj):
        return float(obj.service_commission_percent or 0)

    @staticmethod
    def resolve_product_commission_percent(obj):
        return float(obj.product_commission_percent or 0)


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
    can_field_visit: bool = False
    profile_status: str | None = None
    bio: str | None = None
    compensation_type: str = "fixed"
    fixed_order_payment: float = 0
    service_commission_percent: float = 0
    product_commission_percent: float = 0


class UserUpdateSchema(Schema):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role_id: int | None = None
    shop_ids: list[int] | None = None
    is_director: bool | None = None
    can_field_visit: bool | None = None
    is_active: bool | None = None
    profile_status: str | None = None
    bio: str | None = None
    compensation_type: str | None = None
    fixed_order_payment: float | None = None
    service_commission_percent: float | None = None
    product_commission_percent: float | None = None


class PasswordResetSchema(Schema):
    password: str


class ShopCreateSchema(Schema):
    name: str
    code: str
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str = "Europe/Moscow"
    currency: str = "RUB"
    is_active: bool = True


class ShopUpdateSchema(Schema):
    name: str | None = None
    code: str | None = None
    city: str | None = None
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


def _has_admin_permission(request, *codenames):
    user = request.auth
    return (
        user.is_superuser
        or user.is_director
        or any(user.has_permission(codename) for codename in codenames)
    )


def _ensure_admin_permission(request, *codenames):
    if not _has_admin_permission(request, *codenames):
        raise PermissionError("Нет прав для администрирования")


def _has_global_shop_admin(request):
    user = request.auth
    return (
        user.is_superuser
        or user.is_director
        or user.has_permission("settings.view_all_shops")
    )


def _ensure_director_admin(request):
    if not (request.auth.is_superuser or request.auth.is_director):
        raise PermissionError("Только директор может назначать статус директора")


def _get_assignable_shops(request):
    if _has_global_shop_admin(request):
        return Shop.objects.filter(is_active=True)
    return request.auth.get_available_shops()


def _get_manageable_users(request):
    User = get_user_model()
    queryset = (
        User.objects.select_related("role", "current_shop")
        .prefetch_related("shops", "role__permissions")
        .order_by("username")
    )
    if _has_global_shop_admin(request):
        return queryset

    available_shops = request.auth.get_available_shops()
    return queryset.filter(
        models.Q(id=request.auth.id) | models.Q(shops__in=available_shops)
    ).distinct()


def _sync_user_shops(request, user, shop_ids):
    _ensure_admin_permission(request, "users.manage_shop_access")
    assignable_shops = _get_assignable_shops(request)
    shops = assignable_shops.filter(id__in=shop_ids)
    if len(set(shop_ids)) != shops.count():
        raise PermissionError("Нет прав назначать один из выбранных филиалов")

    user.shops.set(shops)
    if user.current_shop_id not in set(shops.values_list("id", flat=True)):
        user.current_shop = shops.first()
        user.save(update_fields=["current_shop"])


@router.get("/users", response=list[AdminUserSchema])
def list_users(request, page: int = 1, page_size: int = 20):
    _ensure_admin_permission(request, "users.view_user")
    offset = max(page - 1, 0) * page_size
    return _get_manageable_users(request)[offset : offset + page_size]


@router.post("/users", response={201: AdminUserSchema, 400: dict})
def create_user(request, data: UserCreateSchema):
    _ensure_admin_permission(request, "users.add_user")
    if data.role_id:
        _ensure_admin_permission(request, "users.manage_permissions")
    if data.is_director:
        _ensure_director_admin(request)
    if data.shop_ids:
        _ensure_admin_permission(request, "users.manage_shop_access")
    if (
        data.compensation_type != "fixed"
        or data.fixed_order_payment
        or data.service_commission_percent
        or data.product_commission_percent
    ):
        _ensure_admin_permission(request, "users.manage_compensation")

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
        can_field_visit=data.can_field_visit,
        profile_status=data.profile_status or "",
        bio=data.bio or "",
        compensation_type=data.compensation_type,
        fixed_order_payment=data.fixed_order_payment,
        service_commission_percent=data.service_commission_percent,
        product_commission_percent=data.product_commission_percent,
    )
    if data.shop_ids:
        _sync_user_shops(request, user, data.shop_ids)
    return 201, user


@router.get("/users/{user_id}", response=AdminUserSchema)
def get_user(request, user_id: int):
    _ensure_admin_permission(request, "users.view_user")
    return get_object_or_404(_get_manageable_users(request), id=user_id)


@router.put("/users/{user_id}", response=AdminUserSchema)
def update_user(request, user_id: int, data: UserUpdateSchema):
    _ensure_admin_permission(request, "users.change_user")
    user = get_object_or_404(_get_manageable_users(request), id=user_id)
    incoming = data.model_dump(exclude_unset=True)
    shop_ids = incoming.pop("shop_ids", None)
    role_id = incoming.pop("role_id", None)
    compensation_fields = {
        "compensation_type",
        "fixed_order_payment",
        "service_commission_percent",
        "product_commission_percent",
    }
    if compensation_fields.intersection(incoming):
        _ensure_admin_permission(request, "users.manage_compensation")
    if role_id is not None:
        _ensure_admin_permission(request, "users.manage_permissions")
        user.role = Role.objects.filter(id=role_id).first()
    if "is_director" in incoming:
        _ensure_director_admin(request)
    for field, value in incoming.items():
        if value is not None:
            setattr(user, field, value)
    user.save()
    if shop_ids is not None:
        _sync_user_shops(request, user, shop_ids)
    return get_user(request, user.id)


@router.delete("/users/{user_id}", response={200: dict, 403: dict})
def delete_user(request, user_id: int):
    _ensure_admin_permission(request, "users.delete_user")
    user = get_object_or_404(_get_manageable_users(request), id=user_id)
    if user.id == request.auth.id:
        return 403, {"error": "Нельзя удалить текущего пользователя"}
    user.delete()
    return {"success": True}


@router.post("/users/{user_id}/reset-password", response=dict)
def reset_user_password(request, user_id: int, data: PasswordResetSchema):
    _ensure_admin_permission(request, "users.change_user")
    user = get_object_or_404(_get_manageable_users(request), id=user_id)
    user.set_password(data.password)
    user.save(update_fields=["password"])
    return {"success": True}


@router.get("/shops", response=list[AdminShopSchema])
def list_admin_shops(request):
    _ensure_admin_permission(request, "settings.view_shop", "users.manage_shop_access")
    if _has_global_shop_admin(request):
        return Shop.objects.all().order_by("name")
    return request.auth.get_available_shops().order_by("name")


@router.post("/shops", response={201: AdminShopSchema, 400: dict})
def create_shop(request, data: ShopCreateSchema):
    _ensure_admin_permission(request, "settings.add_shop")
    if Shop.objects.filter(code=data.code).exists():
        return 400, {"error": "Филиал с таким кодом уже существует"}
    shop = Shop.objects.create(**data.model_dump())
    return 201, shop


@router.get("/shops/{shop_id}", response=AdminShopSchema)
def get_admin_shop(request, shop_id: int):
    _ensure_admin_permission(request, "settings.view_shop")
    return get_object_or_404(_get_assignable_shops(request), id=shop_id)


@router.put("/shops/{shop_id}", response=AdminShopSchema)
def update_shop(request, shop_id: int, data: ShopUpdateSchema):
    _ensure_admin_permission(request, "settings.change_shop")
    shop = get_object_or_404(_get_assignable_shops(request), id=shop_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(shop, field, value)
    shop.save()
    return shop


@router.delete("/shops/{shop_id}", response=dict)
def delete_shop(request, shop_id: int):
    _ensure_admin_permission(request, "settings.delete_shop")
    shop = get_object_or_404(_get_assignable_shops(request), id=shop_id)
    shop.is_active = False
    shop.save(update_fields=["is_active"])
    return {"success": True}


@router.get("/roles", response=list[AdminRoleSchema])
def list_roles(request):
    _ensure_admin_permission(request, "users.manage_permissions")
    return Role.objects.prefetch_related("permissions").order_by("name")


@router.post("/roles", response={201: AdminRoleSchema, 400: dict})
def create_role(request, data: RoleCreateSchema):
    _ensure_admin_permission(request, "users.manage_permissions")
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
    _ensure_admin_permission(request, "users.manage_permissions")
    return get_object_or_404(Role.objects.prefetch_related("permissions"), id=role_id)


@router.put("/roles/{role_id}", response=AdminRoleSchema)
def update_role(request, role_id: int, data: RoleUpdateSchema):
    _ensure_admin_permission(request, "users.manage_permissions")
    role = get_object_or_404(Role, id=role_id)
    incoming = data.model_dump(exclude_unset=True)
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
    _ensure_admin_permission(request, "users.manage_permissions")
    role = get_object_or_404(Role, id=role_id)
    role.delete()
    return {"success": True}


@router.get("/permissions", response=list[AdminPermissionSchema])
def list_permissions(request):
    _ensure_admin_permission(request, "users.manage_permissions")
    return Permission.objects.all().order_by("category", "name")


@router.get("/employees/statistics", response=dict)
def get_employees_statistics(
    request,
    period: str = "month",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    all_shops: bool = False,
):
    """Статистика сотрудников и расчет оплаты за выбранный период."""
    _ensure_admin_permission(request, "users.view_user", "reports.view_dashboard")
    start_date, end_date = resolve_period_range(period, date_from, date_to)

    if all_shops:
        if not request.auth.can_view_global_statistics():
            raise PermissionError("Нет прав для общей статистики по филиалам")
        shops = None
    elif getattr(request, "current_shop", None) is not None:
        shops = Shop.objects.filter(id=request.current_shop.id)
    else:
        shops = request.auth.get_available_shops()

    return {
        "period": {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
        },
        "items": employees_statistics_queryset(
            request.auth,
            start_date,
            end_date,
            shops=shops,
        ),
    }


@router.get("/statistics", response=dict)
def get_system_statistics(request, all_shops: bool = False):
    """Сводные показатели для главной страницы администрирования."""
    if not (
        request.auth.is_superuser
        or request.auth.is_director
        or request.auth.has_permission("users.view_user")
        or request.auth.has_permission("settings.view_shop")
        or request.auth.has_permission("reports.view_dashboard")
    ):
        raise PermissionError("Нет прав для просмотра системной статистики")

    User = get_user_model()
    today = timezone.localdate()
    orders = Order.objects.filter(created_at__date=today)
    global_stats = False

    if all_shops:
        if not request.auth.can_view_global_statistics():
            raise PermissionError("Нет прав для общей статистики по филиалам")
        global_stats = True
    elif getattr(request, "current_shop", None) is not None:
        orders = orders.filter(shop=request.current_shop)
    else:
        orders = orders.filter(shop__in=request.auth.get_available_shops())

    users = User.objects.all() if global_stats else _get_manageable_users(request)
    shops = Shop.objects.all() if global_stats else request.auth.get_available_shops()
    today_revenue = orders.aggregate(total=Sum("final_cost"))["total"] or 0

    return {
        "total_users": users.count(),
        "active_users": users.filter(is_active=True).count(),
        "total_shops": shops.count(),
        "active_shops": shops.filter(is_active=True).count(),
        "total_orders_today": orders.count(),
        "total_revenue_today": float(today_revenue),
        "system_health": "good",
    }
