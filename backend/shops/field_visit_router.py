from decimal import Decimal

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from core.api_app import AuthBearer
from shops.models import Shop, ShopSettings
from users.models import User

router = Router(tags=["Выезд мастера"], auth=AuthBearer())


class FieldVisitZoneSchema(Schema):
    id: str
    name: str
    price: float = 0.0
    geometry: dict  # GeoJSON Polygon or Circle


class FieldVisitConfigSchema(Schema):
    enabled: bool
    service_name: str
    base_price: float
    out_of_zone_price: float
    description: str
    zones: list[FieldVisitZoneSchema]
    advance_days: int


class FieldVisitConfigUpdateSchema(Schema):
    enabled: bool | None = None
    service_name: str | None = None
    base_price: float | None = None
    out_of_zone_price: float | None = None
    description: str | None = None
    zones: list[FieldVisitZoneSchema] | None = None
    advance_days: int | None = None


class FieldVisitWorkerSchema(Schema):
    id: int
    name: str
    avatar_url: str | None = None


def _check_shop_access(request, shop: Shop) -> None:
    """Raise 403 if the authenticated user has no access to this shop."""
    from ninja.errors import HttpError

    user = request.auth
    if user.is_superuser or user.is_director:
        return
    if not user.shops.filter(id=shop.id).exists():
        raise HttpError(403, "Нет доступа к этому магазину")


@router.get("/shops/{shop_id}/field-visit", response=FieldVisitConfigSchema)
def get_field_visit_config(request, shop_id: int) -> FieldVisitConfigSchema:
    shop = get_object_or_404(Shop, id=shop_id)
    _check_shop_access(request, shop)
    settings, _ = ShopSettings.objects.get_or_create(shop=shop)
    return FieldVisitConfigSchema(
        enabled=settings.field_visit_enabled,
        service_name=settings.field_visit_service_name,
        base_price=float(settings.field_visit_base_price),
        out_of_zone_price=float(settings.field_visit_out_of_zone_price),
        description=settings.field_visit_description,
        zones=settings.field_visit_zones or [],
        advance_days=settings.field_visit_advance_days,
    )


@router.patch("/shops/{shop_id}/field-visit", response=FieldVisitConfigSchema)
def update_field_visit_config(
    request, shop_id: int, data: FieldVisitConfigUpdateSchema
) -> FieldVisitConfigSchema:
    from ninja.errors import HttpError

    shop = get_object_or_404(Shop, id=shop_id)
    _check_shop_access(request, shop)
    if not request.auth.has_permission("shops.change_shopsettings"):
        raise HttpError(403, "Нет прав для изменения настроек магазина")
    settings, _ = ShopSettings.objects.get_or_create(shop=shop)
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        if field == "zones":
            db_field = "field_visit_zones"
        elif field == "enabled":
            db_field = "field_visit_enabled"
        elif field == "service_name":
            db_field = "field_visit_service_name"
        elif field == "base_price":
            db_field = "field_visit_base_price"
            value = Decimal(str(value))
        elif field == "out_of_zone_price":
            db_field = "field_visit_out_of_zone_price"
            value = Decimal(str(value))
        elif field == "description":
            db_field = "field_visit_description"
        elif field == "advance_days":
            db_field = "field_visit_advance_days"
        else:
            db_field = f"field_visit_{field}"
        setattr(settings, db_field, value)
    settings.save()
    return get_field_visit_config(request, shop_id)


@router.get(
    "/shops/{shop_id}/field-visit/workers", response=list[FieldVisitWorkerSchema]
)
def get_field_visit_workers(request, shop_id: int) -> list[FieldVisitWorkerSchema]:
    shop = get_object_or_404(Shop, id=shop_id)
    _check_shop_access(request, shop)
    workers = User.objects.filter(shops=shop, can_field_visit=True, is_active=True)
    return [
        FieldVisitWorkerSchema(
            id=w.id,
            name=f"{w.last_name} {w.first_name}".strip() or w.username,
            avatar_url=w.avatar.url if w.avatar else None,
        )
        for w in workers
    ]
