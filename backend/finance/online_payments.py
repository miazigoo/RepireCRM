from __future__ import annotations

from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from orders.models import Order
from shops.models import Organization, SubscriptionPlan
from shops.subscription_services import (
    change_subscription_plan,
    notify_subscription_if_needed,
)

from .fiscal_receipts import (
    build_payment_receipt_snapshot,
    create_or_update_payment_receipt,
    receipt_snapshot_to_yookassa,
)
from .models import OnlinePayment, Payment, PaymentMethod, PaymentReceipt

ALLOWED_METHOD_TYPES = {
    OnlinePayment.PaymentMethodType.ANY,
    OnlinePayment.PaymentMethodType.BANK_CARD,
    OnlinePayment.PaymentMethodType.SBP,
    OnlinePayment.PaymentMethodType.YOO_MONEY,
}

METHOD_LABELS = {
    OnlinePayment.PaymentMethodType.ANY: ("yookassa_online", "ЮKassa: платежная форма"),
    OnlinePayment.PaymentMethodType.BANK_CARD: (
        "yookassa_bank_card",
        "ЮKassa: банковская карта",
    ),
    OnlinePayment.PaymentMethodType.SBP: ("yookassa_sbp", "ЮKassa: СБП"),
    OnlinePayment.PaymentMethodType.YOO_MONEY: ("yookassa_yoomoney", "ЮKassa: ЮMoney"),
}


def normalize_method_type(method_type: str | None) -> str:
    method = method_type or OnlinePayment.PaymentMethodType.BANK_CARD
    if method not in ALLOWED_METHOD_TYPES:
        raise ValueError("Неподдерживаемый способ онлайн-оплаты")
    return method


def get_or_create_online_payment_method(method_type: str) -> PaymentMethod:
    code, name = METHOD_LABELS[method_type]
    payment_method, _ = PaymentMethod.objects.get_or_create(
        code=code,
        defaults={
            "name": name,
            "description": "Онлайн-оплата через ЮKassa",
            "is_cash": False,
            "is_active": True,
        },
    )
    return payment_method


def _backend_url(path: str) -> str:
    return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{path}"


def _mock_confirmation_url(payment: OnlinePayment) -> str:
    path = f"/api/finance/online-payments/{payment.id}/test-checkout"
    return _backend_url(f"{path}?token={payment.test_token}")


def _provider_status(status: str) -> str:
    if status == "succeeded":
        return OnlinePayment.Status.SUCCEEDED
    if status == "waiting_for_capture":
        return OnlinePayment.Status.WAITING_FOR_CAPTURE
    if status == "canceled":
        return OnlinePayment.Status.CANCELED
    if status == "pending":
        return OnlinePayment.Status.PENDING
    return OnlinePayment.Status.FAILED


def _yookassa_payload(payment: OnlinePayment) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "amount": {
            "value": f"{payment.amount:.2f}",
            "currency": payment.currency,
        },
        "capture": settings.YOOKASSA_CAPTURE,
        "confirmation": {
            "type": "redirect",
            "return_url": payment.return_url,
        },
        "description": payment.description[:128],
        "metadata": {
            "online_payment_id": str(payment.id),
            "purpose": payment.purpose,
        },
    }

    if payment.payment_method_type != OnlinePayment.PaymentMethodType.ANY:
        payload["payment_method_data"] = {"type": payment.payment_method_type}

    if payment.fiscal_receipt_snapshot:
        payload["receipt"] = receipt_snapshot_to_yookassa(
            payment.fiscal_receipt_snapshot
        )

    return payload


def _shop_fiscal_enabled(order: Order) -> bool:
    return bool(
        getattr(getattr(order.shop, "settings", None), "fiscalization_enabled", False)
    )


def _prepare_online_order_receipt(payment: OnlinePayment, order: Order) -> None:
    if not _shop_fiscal_enabled(order):
        return

    method = get_or_create_online_payment_method(payment.payment_method_type)
    draft_local_payment = Payment(
        payment_number=f"ONLINE-{payment.id}",
        payment_type=Payment.PaymentType.INCOME,
        status=Payment.PaymentStatus.PENDING,
        amount=payment.amount,
        fee_amount=Decimal("0"),
        payment_method=method,
        order=order,
        description=payment.description,
        reference_number=str(payment.idempotence_key),
        external_id=payment.provider_payment_id,
        payment_date=timezone.now(),
        created_by=payment.created_by,
    )
    snapshot = build_payment_receipt_snapshot(
        draft_local_payment,
        require_customer_contact=True,
    )
    payment.fiscal_receipt_snapshot = snapshot
    payment.fiscal_receipt_error = ""
    payment.save(update_fields=["fiscal_receipt_snapshot", "fiscal_receipt_error"])


def create_provider_payment(payment: OnlinePayment) -> OnlinePayment:
    if settings.YOOKASSA_MOCK:
        payment.provider_payment_id = f"test_{payment.idempotence_key}"
        payment.status = OnlinePayment.Status.PENDING
        payment.confirmation_url = _mock_confirmation_url(payment)
        payment.raw_payload = {
            "mode": "mock",
            "id": payment.provider_payment_id,
            "status": payment.status,
            "receipt": payment.fiscal_receipt_snapshot,
        }
        payment.save(
            update_fields=[
                "provider_payment_id",
                "status",
                "confirmation_url",
                "raw_payload",
                "updated_at",
            ]
        )
        return payment

    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        raise ValueError("Не настроены YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY")

    response = requests.post(
        f"{settings.YOOKASSA_API_URL.rstrip('/')}/payments",
        auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        headers={
            "Idempotence-Key": str(payment.idempotence_key),
            "Content-Type": "application/json",
        },
        json=_yookassa_payload(payment),
        timeout=20,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text[:500]}

    if response.status_code >= 400:
        raise ValueError(
            payload.get("description") or payload.get("error") or "Ошибка ЮKassa"
        )

    payment.provider_payment_id = payload["id"]
    payment.status = _provider_status(payload.get("status", "pending"))
    payment.confirmation_url = payload.get("confirmation", {}).get(
        "confirmation_url", ""
    )
    payment.raw_payload = payload
    payment.save(
        update_fields=[
            "provider_payment_id",
            "status",
            "confirmation_url",
            "raw_payload",
            "updated_at",
        ]
    )
    if payment.status == OnlinePayment.Status.SUCCEEDED:
        return apply_successful_online_payment(payment)
    return payment


def sync_provider_payment(payment: OnlinePayment) -> OnlinePayment:
    if settings.YOOKASSA_MOCK:
        return payment

    if not payment.provider_payment_id:
        return payment

    payment_url = (
        f"{settings.YOOKASSA_API_URL.rstrip('/')}/payments/"
        f"{payment.provider_payment_id}"
    )
    response = requests.get(
        payment_url,
        auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        timeout=20,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text[:500]}
    if response.status_code >= 400:
        raise ValueError(
            payload.get("description")
            or payload.get("error")
            or "Ошибка синхронизации ЮKassa"
        )

    return update_payment_from_provider_payload(payment, payload)


def update_payment_from_provider_payload(
    payment: OnlinePayment, payload: dict[str, Any]
) -> OnlinePayment:
    status = _provider_status(payload.get("status", payment.status))
    payment.status = status
    payment.raw_payload = payload
    payment.save(update_fields=["status", "raw_payload", "updated_at"])

    if status == OnlinePayment.Status.SUCCEEDED:
        return apply_successful_online_payment(payment)

    return payment


def create_order_online_payment(
    *,
    order: Order,
    amount: Decimal,
    method_type: str,
    created_by,
    return_url: str,
) -> OnlinePayment:
    method = normalize_method_type(method_type)
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if amount > order.remaining_payment:
        raise ValueError(
            f"Сумма оплаты превышает остаток ({order.remaining_payment:.2f})"
        )

    payment = OnlinePayment.objects.create(
        purpose=OnlinePayment.Purpose.ORDER,
        payment_method_type=method,
        amount=amount,
        currency=order.shop.currency or "RUB",
        description=f"Оплата заказа {order.order_number}",
        order=order,
        created_by=created_by,
        return_url=return_url,
    )
    _prepare_online_order_receipt(payment, order)
    return create_provider_payment(payment)


def create_subscription_online_payment(
    *,
    organization: Organization,
    plan: SubscriptionPlan,
    method_type: str,
    created_by,
    return_url: str,
) -> OnlinePayment:
    method = normalize_method_type(method_type)
    if plan.price <= 0:
        raise ValueError("Этот тариф не требует оплаты")

    payment = OnlinePayment.objects.create(
        purpose=OnlinePayment.Purpose.SUBSCRIPTION,
        payment_method_type=method,
        amount=plan.price,
        currency="RUB",
        description=f"Оплата подписки {plan.name}",
        organization=organization,
        subscription_plan=plan,
        created_by=created_by,
        return_url=return_url,
    )
    return create_provider_payment(payment)


@transaction.atomic
def apply_successful_online_payment(payment: OnlinePayment) -> OnlinePayment:
    locked = OnlinePayment.objects.select_for_update().get(id=payment.id)

    if (
        locked.status == OnlinePayment.Status.SUCCEEDED
        and locked.paid_at
        and (
            locked.local_payment_id
            or locked.purpose == OnlinePayment.Purpose.SUBSCRIPTION
        )
    ):
        return locked

    locked.status = OnlinePayment.Status.SUCCEEDED
    locked.paid_at = locked.paid_at or timezone.now()

    if locked.purpose == OnlinePayment.Purpose.ORDER:
        if not locked.order_id:
            raise ValueError("Онлайн-платеж не привязан к заказу")

        order = Order.objects.select_for_update().get(id=locked.order_id)
        if not locked.local_payment_id:
            payment_method = get_or_create_online_payment_method(
                locked.payment_method_type
            )
            local_payment = Payment.objects.create(
                payment_type=Payment.PaymentType.INCOME,
                status=Payment.PaymentStatus.COMPLETED,
                amount=locked.amount,
                fee_amount=Decimal("0"),
                payment_method=payment_method,
                order=order,
                description=locked.description,
                reference_number=locked.provider_payment_id,
                external_id=locked.provider_payment_id,
                payment_date=locked.paid_at,
                processed_at=locked.paid_at,
                created_by=locked.created_by,
            )
            receipt = create_or_update_payment_receipt(local_payment)
            if receipt and locked.fiscal_receipt_snapshot:
                receipt.provider = locked.provider
                receipt.status = PaymentReceipt.Status.SENT
                receipt.normalized_snapshot = locked.fiscal_receipt_snapshot
                receipt.provider_payload = receipt_snapshot_to_yookassa(
                    locked.fiscal_receipt_snapshot
                )
                receipt.save(
                    update_fields=[
                        "provider",
                        "status",
                        "normalized_snapshot",
                        "provider_payload",
                        "updated_at",
                    ]
                )
            locked.local_payment = local_payment
            order.prepayment = (order.prepayment or Decimal("0")) + locked.amount
            order.save(update_fields=["prepayment", "updated_at"])

    elif locked.purpose == OnlinePayment.Purpose.SUBSCRIPTION:
        if not locked.organization_id or not locked.subscription_plan_id:
            raise ValueError("Онлайн-платеж не привязан к подписке")
        subscription = change_subscription_plan(
            locked.organization,
            locked.subscription_plan.code,
        )
        notify_subscription_if_needed(subscription)

    locked.save(
        update_fields=[
            "status",
            "paid_at",
            "local_payment",
            "updated_at",
        ]
    )
    return locked
