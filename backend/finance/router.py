from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from inventory.models import RetailSale
from orders.models import Order

from .models import CashRegister, Payment, PaymentMethod

router = Router(tags=["Финансы"])


def _check_perm(request, codename: str):
    return request.auth.has_permission(codename) or request.auth.has_permission(
        codename.replace("finance.", "payments.")
    )


@router.post("/order/{order_id}/create", response=dict)
def create_payment_for_order(request, order_id: int, data: dict):
    """
    Создать платеж по заказу
    """
    if not _check_perm(request, "finance.add_payment"):
        raise PermissionError("Нет прав для создания платежей")

    order = get_object_or_404(Order, id=order_id)
    pm = get_object_or_404(PaymentMethod, id=data["payment_method_id"])
    cr = None
    if pm.is_cash:
        cr = get_object_or_404(CashRegister, id=data.get("cash_register_id"))

    amount = Decimal(str(data["amount"]))
    fee_amount = Decimal(str(data.get("fee_amount", "0")))
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
        description=data.get("description", ""),
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


@router.post("/sales/{sale_id}/pay", response=dict)
def pay_retail_sale(request, sale_id: int, data: dict):
    if not request.auth.has_permission("finance.add_payment"):
        raise PermissionError("Нет прав для создания платежей")
    sale = get_object_or_404(RetailSale, id=sale_id)
    pm = get_object_or_404(PaymentMethod, id=data["payment_method_id"])
    cr = None
    if pm.is_cash and data.get("cash_register_id"):
        cr = get_object_or_404(CashRegister, id=data["cash_register_id"])
    amount = Decimal(str(data.get("amount", sale.total_amount)))
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
        description=data.get("description", f"Оплата продажи {sale.sale_number}"),
        reference_number=sale.sale_number,
        payment_date=timezone.now(),
        created_by=request.auth,
    )
    if cr:
        cr.cash_balance = cr.cash_balance + amount
        cr.save(update_fields=["cash_balance"])
    return {"success": True, "payment_id": p.id, "payment_number": p.payment_number}
