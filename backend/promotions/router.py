from __future__ import annotations

from decimal import Decimal
from typing import List

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router

from customers.models import Customer
from orders.models import Order
from Schemas.common import ErrorSchema

from .models import PromoCode, Promotion
from .schemas import (
    ApplyPromoCodeSchema,
    DiscountQuoteSchema,
    ManualDiscountCreateSchema,
    OrderDiscountSchema,
    PromoCodeCreateSchema,
    PromoCodeSchema,
    PromoCodeUpdateSchema,
    PromoCodeValidateSchema,
    PromotionCreateSchema,
    PromotionSchema,
    PromotionUpdateSchema,
)
from .services import (
    PromotionError,
    active_for_shop,
    apply_promo_code_to_order,
    create_manual_discount,
    order_subtotal,
    quote_promo_code,
    remove_order_discount,
)

router = Router(tags=["Акции и промокоды"])


def _current_shop(request):
    return getattr(request, "current_shop", None)


def _ensure_permission(request, codename: str):
    if not request.auth.has_permission(codename):
        raise PermissionError("Недостаточно прав")


def _available_shops(request, shop_ids: list[int]):
    if not shop_ids:
        return []
    shops = request.auth.get_available_shops().filter(id__in=shop_ids)
    if shops.count() != len(set(shop_ids)):
        raise PermissionError("Нет прав назначить акцию одному из филиалов")
    return shops


def _get_accessible_order(request, order_id: int) -> Order:
    order = get_object_or_404(
        Order.objects.select_related("shop", "customer"), id=order_id
    )
    if not request.auth.can_access_shop(order.shop):
        raise PermissionError("Нет доступа к заказу")
    current_shop = _current_shop(request)
    if current_shop and order.shop_id != current_shop.id:
        raise PermissionError("Переключите филиал, чтобы изменить скидки заказа")
    return order


def _sync_promotion_shops(request, promotion: Promotion, shop_ids: list[int]):
    shops = _available_shops(request, shop_ids)
    promotion.shops.set(shops)


@router.get("/campaigns", response=List[PromotionSchema])
def list_promotions(request, include_inactive: bool = False):
    _ensure_permission(request, "promotions.view_promotion")
    queryset = Promotion.objects.prefetch_related("shops")
    if not include_inactive:
        queryset = active_for_shop(queryset, _current_shop(request))
    elif _current_shop(request):
        queryset = queryset.filter(
            Q(shops__isnull=True) | Q(shops=_current_shop(request))
        ).distinct()
    return queryset.order_by("-is_active", "-created_at")


@router.post("/campaigns", response={201: PromotionSchema, 400: ErrorSchema})
def create_promotion(request, data: PromotionCreateSchema):
    _ensure_permission(request, "promotions.change_promotion")
    incoming = data.dict()
    shop_ids = incoming.pop("shop_ids", [])
    promotion = Promotion.objects.create(created_by=request.auth, **incoming)
    _sync_promotion_shops(request, promotion, shop_ids)
    return 201, promotion


@router.put(
    "/campaigns/{promotion_id}", response={200: PromotionSchema, 404: ErrorSchema}
)
def update_promotion(request, promotion_id: int, data: PromotionUpdateSchema):
    _ensure_permission(request, "promotions.change_promotion")
    promotion = get_object_or_404(Promotion, id=promotion_id)
    incoming = data.dict(exclude_unset=True)
    shop_ids = incoming.pop("shop_ids", None)
    for field, value in incoming.items():
        setattr(promotion, field, value)
    promotion.save()
    if shop_ids is not None:
        _sync_promotion_shops(request, promotion, shop_ids)
    return promotion


@router.delete("/campaigns/{promotion_id}", response=dict)
def disable_promotion(request, promotion_id: int):
    _ensure_permission(request, "promotions.change_promotion")
    promotion = get_object_or_404(Promotion, id=promotion_id)
    promotion.is_active = False
    promotion.save(update_fields=["is_active", "updated_at"])
    return {"success": True}


@router.get("/codes", response=List[PromoCodeSchema])
def list_promo_codes(request, include_inactive: bool = False):
    _ensure_permission(request, "promotions.view_promotion")
    queryset = PromoCode.objects.select_related("promotion").prefetch_related(
        "promotion__shops"
    )
    if not include_inactive:
        queryset = queryset.filter(is_active=True, promotion__is_active=True)
    current_shop = _current_shop(request)
    if current_shop:
        queryset = queryset.filter(
            Q(promotion__shops__isnull=True) | Q(promotion__shops=current_shop)
        ).distinct()
    return queryset.order_by("-is_active", "code")


@router.post("/codes", response={201: PromoCodeSchema, 400: ErrorSchema})
def create_promo_code(request, data: PromoCodeCreateSchema):
    _ensure_permission(request, "promotions.change_promotion")
    promotion = get_object_or_404(Promotion, id=data.promotion_id)
    promo_code = PromoCode.objects.create(
        promotion=promotion,
        code=data.code,
        description=data.description or "",
        is_active=data.is_active,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        usage_limit=data.usage_limit,
        per_customer_limit=data.per_customer_limit,
    )
    return 201, promo_code


@router.put("/codes/{code_id}", response={200: PromoCodeSchema, 404: ErrorSchema})
def update_promo_code(request, code_id: int, data: PromoCodeUpdateSchema):
    _ensure_permission(request, "promotions.change_promotion")
    promo_code = get_object_or_404(PromoCode, id=code_id)
    incoming = data.dict(exclude_unset=True)
    promotion_id = incoming.pop("promotion_id", None)
    if promotion_id:
        promo_code.promotion = get_object_or_404(Promotion, id=promotion_id)
    for field, value in incoming.items():
        setattr(promo_code, field, value)
    promo_code.save()
    return promo_code


@router.delete("/codes/{code_id}", response=dict)
def disable_promo_code(request, code_id: int):
    _ensure_permission(request, "promotions.change_promotion")
    promo_code = get_object_or_404(PromoCode, id=code_id)
    promo_code.is_active = False
    promo_code.save(update_fields=["is_active", "updated_at"])
    return {"success": True}


@router.post("/validate-code", response=DiscountQuoteSchema)
def validate_promo_code(request, data: PromoCodeValidateSchema):
    _ensure_permission(request, "promotions.apply_discount")
    order = None
    customer = None
    subtotal = Decimal(str(data.subtotal)) if data.subtotal is not None else None
    if data.order_id:
        order = _get_accessible_order(request, data.order_id)
        subtotal = order_subtotal(order)
        customer = order.customer
    elif data.customer_id:
        customer = get_object_or_404(Customer, id=data.customer_id)
    return quote_promo_code(
        data.code, order=order, customer=customer, subtotal=subtotal
    )


@router.post(
    "/orders/{order_id}/apply-code",
    response={201: OrderDiscountSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def apply_code_to_order(request, order_id: int, data: ApplyPromoCodeSchema):
    _ensure_permission(request, "promotions.apply_discount")
    order = _get_accessible_order(request, order_id)
    try:
        return 201, apply_promo_code_to_order(order, data.code, user=request.auth)
    except PromoCode.DoesNotExist:
        return 404, {"error": "Промокод не найден"}
    except PromotionError as exc:
        return 400, {"error": str(exc)}


@router.post(
    "/orders/{order_id}/manual-discount",
    response={201: OrderDiscountSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def add_manual_discount(request, order_id: int, data: ManualDiscountCreateSchema):
    _ensure_permission(request, "promotions.apply_discount")
    order = _get_accessible_order(request, order_id)
    try:
        return 201, create_manual_discount(
            order,
            amount=Decimal(str(data.amount)),
            label=data.label,
            user=request.auth,
        )
    except PromotionError as exc:
        return 400, {"error": str(exc)}


@router.delete(
    "/orders/{order_id}/discounts/{discount_id}", response={200: dict, 404: ErrorSchema}
)
def delete_order_discount(request, order_id: int, discount_id: int):
    _ensure_permission(request, "promotions.apply_discount")
    order = _get_accessible_order(request, order_id)
    try:
        remove_order_discount(order, discount_id, user=request.auth)
    except PromotionError as exc:
        return 404, {"error": str(exc)}
    return {"success": True}
