from decimal import Decimal
from html import escape
from ipaddress import ip_address, ip_network

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from ninja import Router, Schema

from inventory.models import RetailSale
from orders.models import Order

from .models import CashRegister, OnlinePayment, Payment, PaymentMethod
from .online_payments import (
    apply_successful_online_payment,
    create_order_online_payment,
    sync_provider_payment,
    update_payment_from_provider_payload,
)
from .schemas import CreateSalePaymentRequest

router = Router(tags=["Финансы"])


class OrderPaymentCreateSchema(Schema):
    amount: Decimal
    payment_method_id: int
    cash_register_id: int | None = None
    fee_amount: Decimal = Decimal("0")
    description: str = ""


class OnlinePaymentCreateSchema(Schema):
    amount: Decimal | None = None
    payment_method_type: str = OnlinePayment.PaymentMethodType.BANK_CARD
    return_url: str | None = None


class OnlinePaymentSchema(Schema):
    id: int
    provider: str
    purpose: str
    status: str
    payment_method_type: str
    amount: float
    currency: str
    confirmation_url: str
    provider_payment_id: str
    is_test: bool


def _check_perm(request, codename: str):
    return request.auth.has_permission(codename) or request.auth.has_permission(
        codename.replace("finance.", "payments.")
    )


def _serialize_online_payment(payment: OnlinePayment) -> dict:
    return {
        "id": payment.id,
        "provider": payment.provider,
        "purpose": payment.purpose,
        "status": payment.status,
        "payment_method_type": payment.payment_method_type,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "confirmation_url": payment.confirmation_url,
        "provider_payment_id": payment.provider_payment_id,
        "is_test": bool(settings.YOOKASSA_MOCK),
    }


def _can_access_online_payment(request, payment: OnlinePayment) -> bool:
    if payment.order_id:
        return request.auth.can_access_shop(payment.order.shop)

    if payment.organization_id:
        if (
            request.auth.is_superuser
            or request.auth.is_director
            or request.auth.has_permission("settings.view_all_shops")
        ):
            return True
        return (
            request.auth.get_available_shops()
            .filter(settings__organization_id=payment.organization_id)
            .exists()
        )

    return False


def _assert_can_access_online_payment(request, payment: OnlinePayment):
    if not _can_access_online_payment(request, payment):
        raise PermissionError("Нет доступа к платежу")


@router.post("/order/{order_id}/create", response=dict)
def create_payment_for_order(
    request,
    order_id: int,
    data: OrderPaymentCreateSchema,
):
    """
    Создать платеж по заказу
    """
    if not _check_perm(request, "finance.add_payment"):
        raise PermissionError("Нет прав для создания платежей")

    order = get_object_or_404(Order, id=order_id)

    # Проверяем доступ к магазину
    if not request.auth.can_access_shop(order.shop):
        raise PermissionError("Нет доступа к заказу в этом магазине")
    pm = get_object_or_404(PaymentMethod, id=data.payment_method_id)
    cr = None
    if pm.is_cash:
        cr = get_object_or_404(CashRegister, id=data.cash_register_id)

    amount = data.amount
    fee_amount = data.fee_amount
    if amount <= 0:
        return {"error": "Сумма должна быть > 0"}

    remaining = order.remaining_payment
    if amount > remaining:
        return {
            "error": f"Сумма оплаты превышает остаток к оплате ({float(remaining):.2f})"
        }

    p = Payment.objects.create(
        payment_type=Payment.PaymentType.INCOME,
        status=Payment.PaymentStatus.COMPLETED,
        amount=amount,
        fee_amount=fee_amount,
        payment_method=pm,
        cash_register=cr,
        order=order,
        description=data.description,
        payment_date=timezone.now(),
        created_by=request.auth,
    )

    order.prepayment = (order.prepayment or 0) + amount
    order.save(update_fields=["prepayment", "updated_at"])

    if cr:
        cr.cash_balance = cr.cash_balance + amount
        cr.save(update_fields=["cash_balance"])

    return {
        "success": True,
        "payment_id": p.id,
        "payment_number": p.payment_number,
        "net_amount": float(p.net_amount),
    }


@router.post("/order/{order_id}/online-payment", response=OnlinePaymentSchema)
def create_online_payment_for_order(
    request,
    order_id: int,
    data: OnlinePaymentCreateSchema,
):
    """Создать онлайн-оплату заказа через ЮKassa/тестовый checkout."""
    if not _check_perm(request, "finance.add_payment"):
        raise PermissionError("Нет прав для создания платежей")

    order = get_object_or_404(Order, id=order_id)
    if not request.auth.can_access_shop(order.shop):
        raise PermissionError("Нет доступа к заказу в этом магазине")

    amount = data.amount if data.amount is not None else order.remaining_payment
    return_url = (
        data.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/orders/{order.id}"
    )
    payment = create_order_online_payment(
        order=order,
        amount=amount,
        method_type=data.payment_method_type,
        created_by=request.auth,
        return_url=return_url,
    )
    return _serialize_online_payment(payment)


@router.get("/online-payments/{payment_id}", response=OnlinePaymentSchema)
def get_online_payment(request, payment_id: int):
    payment = get_object_or_404(
        OnlinePayment.objects.select_related("order__shop", "organization"),
        id=payment_id,
    )
    _assert_can_access_online_payment(request, payment)
    return _serialize_online_payment(payment)


@router.post("/online-payments/{payment_id}/sync", response=OnlinePaymentSchema)
def sync_online_payment(request, payment_id: int):
    payment = get_object_or_404(
        OnlinePayment.objects.select_related("order__shop", "organization"),
        id=payment_id,
    )
    _assert_can_access_online_payment(request, payment)
    payment = sync_provider_payment(payment)
    return _serialize_online_payment(payment)


@router.get("/online-payments/{payment_id}/test-checkout", auth=None)
def test_online_payment_checkout(request, payment_id: int, token: str):
    payment = get_object_or_404(OnlinePayment, id=payment_id, test_token=token)
    if not settings.YOOKASSA_MOCK:
        return HttpResponse("Тестовая страница отключена", status=404)

    confirm_url = (
        f"/api/finance/online-payments/{payment.id}/test-confirm"
        f"?token={payment.test_token}"
    )
    amount = escape(f"{payment.amount:.2f} {payment.currency}")
    confirm_url = escape(confirm_url, quote=True)
    description = escape(payment.description)
    method_label = escape(payment.get_payment_method_type_display())
    html = f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Тестовая оплата</title>
        <style>
          body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background: #eef2f7;
            color: #111827;
            font-family: Arial, sans-serif;
          }}
          main {{
            width: min(460px, calc(100vw - 32px));
            padding: 28px;
            border: 1px solid #d8e0ea;
            border-radius: 14px;
            background: white;
            box-shadow: 0 24px 60px rgba(15, 23, 42, 0.14);
          }}
          h1 {{ margin: 0 0 8px; font-size: 28px; }}
          p {{ margin: 8px 0; color: #475569; line-height: 1.5; }}
          strong {{ color: #111827; }}
          button {{
            width: 100%;
            min-height: 48px;
            margin-top: 20px;
            border: 0;
            border-radius: 10px;
            background: #2563eb;
            color: white;
            cursor: pointer;
            font-size: 16px;
            font-weight: 800;
          }}
        </style>
      </head>
      <body>
        <main>
          <h1>Тестовая оплата</h1>
          <p>{description}</p>
          <p>Сумма: <strong>{amount}</strong></p>
          <p>Метод: <strong>{method_label}</strong></p>
          <form method="post" action="{confirm_url}">
            <button type="submit">Оплатить тестово</button>
          </form>
        </main>
      </body>
    </html>
    """
    return HttpResponse(html)


@router.post("/online-payments/{payment_id}/test-confirm", auth=None)
def confirm_test_online_payment(request, payment_id: int, token: str):
    payment = get_object_or_404(OnlinePayment, id=payment_id, test_token=token)
    if not settings.YOOKASSA_MOCK:
        return HttpResponse("Тестовая оплата отключена", status=404)
    apply_successful_online_payment(payment)
    return redirect(payment.return_url or settings.FRONTEND_URL)


_YOOKASSA_IP_RANGES = [
    ip_network("185.71.76.0/27"),
    ip_network("185.71.77.0/27"),
    ip_network("77.75.153.0/25"),
    ip_network("77.75.156.11/32"),
    ip_network("77.75.156.35/32"),
    ip_network("77.75.154.128/25"),
    ip_network("2a02:5180::/32"),
]


def _is_yookassa_ip(request) -> bool:
    """Return True if the request originates from a YooKassa notification IP."""
    if settings.YOOKASSA_MOCK:
        return True
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    raw_ip = (
        forwarded.split(",")[0].strip() if forwarded else None
    ) or request.META.get("REMOTE_ADDR", "")
    try:
        addr = ip_address(raw_ip)
    except ValueError:
        return False
    return any(addr in net for net in _YOOKASSA_IP_RANGES)


@router.post("/yookassa/webhook", auth=None)
def yookassa_webhook(request, data: dict):
    if not _is_yookassa_ip(request):
        return HttpResponse(status=403)

    # Refuse to process real webhook payloads in mock mode (misconfiguration guard)
    if settings.YOOKASSA_MOCK and settings.ENVIRONMENT == "production":
        return HttpResponse(status=503)

    event_object = data.get("object") or {}
    provider_payment_id = event_object.get("id")
    if not provider_payment_id:
        return {"success": False, "error": "payment id missing"}

    payment = OnlinePayment.objects.filter(
        provider_payment_id=provider_payment_id
    ).first()
    if not payment:
        return {"success": True, "skipped": "payment not found"}

    if settings.YOOKASSA_MOCK:
        update_payment_from_provider_payload(payment, event_object)
    else:
        sync_provider_payment(payment)
    return {"success": True}


@router.post("/sales/{sale_id}/pay", response=dict)
def pay_retail_sale(request, sale_id: int, data: CreateSalePaymentRequest):
    if not request.auth.has_permission("finance.add_payment"):
        raise PermissionError("Нет прав для создания платежей")
    sale = get_object_or_404(RetailSale, id=sale_id)
    current_shop = getattr(request, "current_shop", None)
    if current_shop and sale.shop_id != current_shop.id:
        raise PermissionError("Нет доступа к продаже в другом филиале")
    if not request.auth.can_access_shop(sale.shop):
        raise PermissionError("Нет доступа к продаже в этом филиале")
    pm = get_object_or_404(PaymentMethod, id=data.payment_method_id)
    cr = None
    if pm.is_cash and data.cash_register_id:
        cr = get_object_or_404(CashRegister, id=data.cash_register_id)
    amount = Decimal(str(data.amount if data.amount else sale.total_amount))
    p = Payment.objects.create(
        payment_type=Payment.PaymentType.INCOME,
        status=Payment.PaymentStatus.COMPLETED,
        amount=amount,
        fee_amount=Decimal("0"),
        payment_method=pm,
        cash_register=cr,
        order=None,
        purchase_order=None,
        expense=None,
        description=data.description or f"Оплата продажи {sale.sale_number}",
        reference_number=sale.sale_number,
        payment_date=timezone.now(),
        created_by=request.auth,
    )
    if cr:
        cr.cash_balance = cr.cash_balance + amount
        cr.save(update_fields=["cash_balance"])
    return {"success": True, "payment_id": p.id, "payment_number": p.payment_number}
