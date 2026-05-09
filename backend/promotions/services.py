from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from customers.models import Customer
from orders.models import Order, OrderAuditLog
from shops.models import Shop

from .models import OrderDiscount, PromoCode, Promotion


class PromotionError(ValueError):
    pass


def as_money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def order_subtotal(order: Order) -> Decimal:
    base_cost = (
        order.final_cost if order.final_cost is not None else order.cost_estimate
    )
    services_cost = sum(
        (
            as_money(service.price) * as_money(service.quantity)
            for service in order.orderservice_set.all()
        ),
        Decimal("0.00"),
    )
    return as_money(base_cost) + services_cost


def order_discount_total(order: Order) -> Decimal:
    return sum((discount.amount for discount in order.discounts.all()), Decimal("0.00"))


def active_for_shop(queryset, shop: Shop | None):
    now = timezone.now()
    queryset = queryset.filter(
        is_active=True,
    ).filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
    queryset = queryset.filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
    if shop is not None:
        queryset = queryset.filter(Q(shops__isnull=True) | Q(shops=shop)).distinct()
    return queryset


def promotion_available_for_order(promotion: Promotion, order: Order) -> bool:
    if not promotion.is_current:
        return False
    if (
        promotion.shops.exists()
        and not promotion.shops.filter(id=order.shop_id).exists()
    ):
        return False
    if (
        promotion.usage_limit is not None
        and promotion.used_count >= promotion.usage_limit
    ):
        return False
    if promotion.per_customer_limit is not None:
        used_by_customer = (
            OrderDiscount.objects.filter(
                promotion=promotion,
                order__customer=order.customer,
            )
            .exclude(order=order)
            .count()
        )
        if used_by_customer >= promotion.per_customer_limit:
            return False
    return True


def promo_code_available_for_order(promo_code: PromoCode, order: Order) -> bool:
    if not promo_code.is_current:
        return False
    if not promotion_available_for_order(promo_code.promotion, order):
        return False
    if (
        promo_code.usage_limit is not None
        and promo_code.used_count >= promo_code.usage_limit
    ):
        return False
    if promo_code.per_customer_limit is not None:
        used_by_customer = (
            OrderDiscount.objects.filter(
                promo_code=promo_code,
                order__customer=order.customer,
            )
            .exclude(order=order)
            .count()
        )
        if used_by_customer >= promo_code.per_customer_limit:
            return False
    return True


def quote_promotion(
    promotion: Promotion,
    subtotal: Decimal,
    order: Order | None = None,
) -> dict[str, Any]:
    if order and not promotion_available_for_order(promotion, order):
        return _quote(
            False, "Акция недоступна для этого заказа", promotion, subtotal, 0
        )
    amount = promotion.calculate_discount(subtotal)
    if amount <= 0:
        return _quote(
            False,
            "Сумма заказа меньше минимальной суммы акции",
            promotion,
            subtotal,
            0,
        )
    return _quote(True, "Скидка может быть применена", promotion, subtotal, amount)


def quote_promo_code(
    code: str,
    order: Order | None = None,
    customer: Customer | None = None,
    subtotal: Decimal | None = None,
) -> dict[str, Any]:
    clean_code = code.strip().upper()
    promo_code = (
        PromoCode.objects.select_related("promotion")
        .prefetch_related("promotion__shops")
        .filter(code=clean_code)
        .first()
    )
    if not promo_code:
        return _quote(False, "Промокод не найден", None, subtotal or 0, 0, clean_code)
    if not promo_code.is_current:
        return _quote(
            False,
            "Промокод не активен или срок действия истек",
            promo_code.promotion,
            subtotal or 0,
            0,
            clean_code,
        )
    if order and not promo_code_available_for_order(promo_code, order):
        return _quote(
            False,
            "Промокод недоступен для этого заказа",
            promo_code.promotion,
            subtotal or 0,
            0,
            clean_code,
        )
    if customer and promo_code.per_customer_limit is not None:
        used_by_customer = OrderDiscount.objects.filter(
            promo_code=promo_code,
            order__customer=customer,
        ).count()
        if used_by_customer >= promo_code.per_customer_limit:
            return _quote(
                False,
                "Клиент уже использовал лимит промокода",
                promo_code.promotion,
                subtotal or 0,
                0,
                clean_code,
            )

    if subtotal is not None:
        current_subtotal = subtotal
    elif order is not None:
        current_subtotal = order_subtotal(order)
    else:
        current_subtotal = Decimal("0.00")
    amount = promo_code.promotion.calculate_discount(current_subtotal)
    if amount <= 0:
        return _quote(
            False,
            "Сумма заказа меньше минимальной суммы промокода",
            promo_code.promotion,
            current_subtotal,
            0,
            clean_code,
        )
    return _quote(
        True,
        "Промокод может быть применен",
        promo_code.promotion,
        current_subtotal,
        amount,
        clean_code,
    )


@transaction.atomic
def apply_promo_code_to_order(order: Order, code: str, user=None) -> OrderDiscount:
    clean_code = code.strip().upper()
    promo_code = (
        PromoCode.objects.select_for_update()
        .select_related("promotion")
        .prefetch_related("promotion__shops")
        .get(code=clean_code)
    )
    if not promo_code_available_for_order(promo_code, order):
        raise PromotionError("Промокод недоступен для этого заказа")
    subtotal = order_subtotal(order)
    amount = promo_code.promotion.calculate_discount(subtotal)
    if amount <= 0:
        raise PromotionError("Скидка по промокоду равна нулю")
    if (
        not promo_code.promotion.stackable
        and order.discounts.exclude(promo_code=promo_code).exists()
    ):
        raise PromotionError("Эта акция не сочетается с другими скидками")
    discount, _ = OrderDiscount.objects.update_or_create(
        order=order,
        promo_code=promo_code,
        defaults={
            "promotion": promo_code.promotion,
            "source": OrderDiscount.Source.PROMO_CODE,
            "label": f"Промокод {promo_code.code}",
            "amount": amount,
            "created_by": user,
        },
    )
    _log_discount_change(
        order,
        user,
        f"Применен промокод {promo_code.code}",
        {"discount_id": discount.id, "amount": str(discount.amount)},
    )
    order.save(update_fields=["updated_at"])
    return discount


@transaction.atomic
def create_manual_discount(
    order: Order, amount: Decimal, label: str, user=None
) -> OrderDiscount:
    subtotal = order_subtotal(order)
    amount = as_money(amount)
    if amount <= 0:
        raise PromotionError("Сумма скидки должна быть больше нуля")
    if amount > subtotal:
        raise PromotionError("Скидка не может быть больше суммы заказа")
    discount = OrderDiscount.objects.create(
        order=order,
        source=OrderDiscount.Source.MANUAL,
        label=(label or "Ручная скидка").strip()[:160],
        amount=amount,
        created_by=user,
    )
    _log_discount_change(
        order,
        user,
        f"Добавлена скидка: {discount.label}",
        {"discount_id": discount.id, "amount": str(discount.amount)},
    )
    order.save(update_fields=["updated_at"])
    return discount


@transaction.atomic
def remove_order_discount(order: Order, discount_id: int, user=None) -> None:
    discount = OrderDiscount.objects.filter(order=order, id=discount_id).first()
    if not discount:
        raise PromotionError("Скидка не найдена")
    label = discount.label
    amount = discount.amount
    deleted, _ = OrderDiscount.objects.filter(order=order, id=discount_id).delete()
    if not deleted:
        raise PromotionError("Скидка не найдена")
    _log_discount_change(
        order,
        user,
        f"Удалена скидка: {label}",
        {"discount_id": discount_id, "amount": str(amount)},
    )
    order.save(update_fields=["updated_at"])


def _log_discount_change(
    order: Order, user, message: str, changes: dict[str, Any]
) -> None:
    OrderAuditLog.objects.create(
        order=order,
        action=OrderAuditLog.ActionChoices.UPDATED,
        actor=user,
        message=message,
        changes=changes,
    )


def _quote(
    valid: bool,
    message: str,
    promotion: Promotion | None,
    subtotal: Decimal | int | float,
    amount: Decimal | int | float,
    code: str | None = None,
) -> dict[str, Any]:
    subtotal = Decimal(subtotal or 0)
    amount = Decimal(amount or 0)
    return {
        "valid": valid,
        "message": message,
        "code": code,
        "promotion_id": promotion.id if promotion else None,
        "promotion_name": promotion.name if promotion else None,
        "subtotal": float(subtotal),
        "discount_amount": float(amount),
        "total_after_discount": float(max(Decimal("0.00"), subtotal - amount)),
    }
