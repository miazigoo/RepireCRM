from typing import List, Optional

from django.shortcuts import get_object_or_404
from ninja import Router

from .models import Organization, Shop, ShopSettings
from .schemas import OrganizationSchema, ShopSchema, ShopSettingsSchema

router = Router(tags=["Магазины"])


@router.get("/", response=List[ShopSchema])
def list_shops(request, active_only: bool = True):
    if not request.auth.has_permission("settings.view_shop"):
        raise PermissionError("Нет прав для просмотра магазинов")
    qs = Shop.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("name")


@router.get("/{shop_id}", response=ShopSchema)
def get_shop(request, shop_id: int):
    if not request.auth.has_permission("settings.view_shop"):
        raise PermissionError("Нет прав")
    return get_object_or_404(Shop, id=shop_id)


@router.get("/{shop_id}/settings", response=ShopSettingsSchema)
def get_shop_settings(request, shop_id: int):
    if not request.auth.has_permission("settings.view_shop"):
        raise PermissionError("Нет прав")
    shop = get_object_or_404(Shop, id=shop_id)
    settings = getattr(shop, "settings", None)
    if not settings:
        settings = ShopSettings.objects.create(shop=shop)
    return settings


@router.put("/{shop_id}/settings", response=ShopSettingsSchema)
def update_shop_settings(request, shop_id: int, data: ShopSettingsSchema):
    if not request.auth.has_permission("settings.change_shop"):
        raise PermissionError("Нет прав")
    shop = get_object_or_404(Shop, id=shop_id)
    settings = getattr(shop, "settings", None)
    if not settings:
        settings = ShopSettings.objects.create(shop=shop)
    # обновляем поля
    for field, value in data.dict().items():
        setattr(settings, field, value)
    settings.save()
    return settings


@router.get("/organizations", response=List[OrganizationSchema])
def list_organizations(request):
    if not request.auth.has_permission("settings.view_shop"):
        raise PermissionError("Нет прав")
    return Organization.objects.all().order_by("name")


@router.post("/organizations", response=OrganizationSchema)
def create_organization(request, data: OrganizationSchema):
    if not request.auth.has_permission("settings.change_shop"):
        raise PermissionError("Нет прав")
    org = Organization.objects.create(**data.dict())
    return org


@router.post("/{shop_id}/link-organization", response=dict)
def link_shop_organization(request, shop_id: int, organization_id: int):
    if not request.auth.has_permission("settings.change_shop"):
        raise PermissionError("Нет прав")
    shop = get_object_or_404(Shop, id=shop_id)
    org = get_object_or_404(Organization, id=organization_id)
    settings = getattr(shop, "settings", None) or ShopSettings.objects.create(shop=shop)
    settings.organization = org
    settings.save(update_fields=["organization"])
    return {"success": True}
