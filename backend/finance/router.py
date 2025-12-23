from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from orders.models import Order

from .models import CashRegister, Payment, PaymentMethod

router = Router(tags=["Платежи"])


@router.post("/order/{order_id}/create", response=dict)
def create_payment_for_order(request, order_id: int, data: dict):
    """
    Создать платеж по заказу:
    data = {
      "amount": 1000.00,
      "payment_method_id": 1,
      "cash_register_id": 2,  # опционально для наличных
      "description": "Предоплата",
      "fee_amount": 0.0
    }
    """
    if not request.auth.has_permission("payments.add_payment"):
        raise PermissionError("Нет прав для создания платежей")

    order = get_object_or_404(Order, id=order_id)

    pm = get_object_or_404(PaymentMethod, id=data["payment_method_id"])
    cr = None
    if pm.is_cash:
        cr = get_object_or_404(CashRegister, id=data["cash_register_id"])

    amount = Decimal(str(data["amount"]))
    fee_amount = Decimal(str(data.get("fee_amount", "0")))

    p = Payment.objects.create(
        payment_type=Payment.PaymentType.INCOME,
        status=Payment.PaymentStatus.COMPLETED,
        amount=amount,
        fee_amount=fee_amount,
        payment_method=pm,
        cash_register=cr,
        order=order,
        description=data.get("description", ""),
        payment_date=timezone.now(),
        created_by=request.auth,
    )

    # Обновим предоплату (если это предоплата) — простая логика:
    order.prepayment = (order.prepayment or 0) + amount
    order.save(update_fields=["prepayment", "updated_at"])

    # Обновим кассу
    if cr:
        cr.cash_balance = cr.cash_balance + amount
        cr.save(update_fields=["cash_balance"])

    return {
        "success": True,
        "payment_id": p.id,
        "payment_number": p.payment_number,
        "net_amount": float(p.net_amount),
    }
