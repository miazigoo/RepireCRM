from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction

from .fiscal_constants import (
    FiscalMeasure,
    FiscalPaymentMode,
    FiscalPaymentSubject,
    FiscalPaymentType,
    FiscalTaxationSystem,
    FiscalVatCode,
)
from .models import Payment, PaymentReceipt, PaymentReceiptItem

MONEY = Decimal("0.01")
QTY = Decimal("0.001")


@dataclass(frozen=True)
class FiscalLine:
    name: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    vat_code: str
    payment_subject: str
    payment_mode: str
    measure: str
    source_type: str = ""
    source_id: int | None = None
    sku: str = ""
    barcode: str = ""
    metadata: dict[str, Any] | None = None


def money(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def quantity(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0.000")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(QTY, rounding=ROUND_HALF_UP)


def _shop_settings(shop):
    return getattr(shop, "settings", None)


def _shop_taxation_system(shop) -> str:
    settings = _shop_settings(shop)
    return getattr(settings, "taxation_system", None) or FiscalTaxationSystem.USN_INCOME


def _shop_fiscal_enabled(shop) -> bool:
    settings = _shop_settings(shop)
    return bool(getattr(settings, "fiscalization_enabled", False))


def _default_vat(shop, subject: str) -> str:
    settings = _shop_settings(shop)
    if subject == FiscalPaymentSubject.COMMODITY:
        return getattr(settings, "default_goods_vat_code", None) or FiscalVatCode.NONE
    return getattr(settings, "default_service_vat_code", None) or FiscalVatCode.NONE


def _vat_for(value: str, shop, subject: str) -> str:
    return value or _default_vat(shop, subject)


def _customer_contact(payment: Payment) -> tuple[str, str]:
    customer = None
    if payment.order_id:
        customer = payment.order.customer
    elif payment.retail_sale_id:
        customer = payment.retail_sale.customer
    if not customer:
        return "", ""
    phone = str(customer.phone) if customer.phone else ""
    return customer.email or "", phone


def _payment_shop(payment: Payment):
    if payment.order_id:
        return payment.order.shop
    if payment.retail_sale_id:
        return payment.retail_sale.shop
    if payment.cash_register_id:
        return payment.cash_register.shop
    return None


def _payment_type(payment: Payment) -> str:
    method = payment.payment_method
    if method.fiscal_payment_type:
        return method.fiscal_payment_type
    return FiscalPaymentType.CASH if method.is_cash else FiscalPaymentType.ELECTRONIC


def _line(
    *,
    name: str,
    amount: Decimal,
    quantity_value: Decimal = Decimal("1"),
    vat_code: str,
    payment_subject: str,
    payment_mode: str,
    measure: str,
    source_type: str = "",
    source_id: int | None = None,
    sku: str = "",
    barcode: str = "",
    metadata: dict[str, Any] | None = None,
) -> FiscalLine:
    qty = quantity(quantity_value)
    line_amount = money(amount)
    unit_price = money(line_amount / qty) if qty else line_amount
    return FiscalLine(
        name=(name or "Позиция чека")[:128],
        quantity=qty,
        unit_price=unit_price,
        amount=line_amount,
        vat_code=vat_code,
        payment_subject=payment_subject,
        payment_mode=payment_mode,
        measure=measure,
        source_type=source_type,
        source_id=source_id,
        sku=sku,
        barcode=barcode,
        metadata=metadata or {},
    )


def _discounted_lines(lines: list[FiscalLine], discount: Decimal) -> list[FiscalLine]:
    discount = money(discount)
    if discount <= 0 or not lines:
        return lines

    total = sum((line.amount for line in lines), Decimal("0.00"))
    if total <= 0:
        return lines

    result: list[FiscalLine] = []
    distributed = Decimal("0.00")
    for index, line in enumerate(lines):
        if index == len(lines) - 1:
            line_discount = discount - distributed
        else:
            line_discount = money(discount * line.amount / total)
            distributed += line_discount
        amount = max(Decimal("0.00"), money(line.amount - line_discount))
        result.append(
            FiscalLine(
                name=line.name,
                quantity=line.quantity,
                unit_price=money(amount / line.quantity) if line.quantity else amount,
                amount=amount,
                vat_code=line.vat_code,
                payment_subject=line.payment_subject,
                payment_mode=line.payment_mode,
                measure=line.measure,
                source_type=line.source_type,
                source_id=line.source_id,
                sku=line.sku,
                barcode=line.barcode,
                metadata={**(line.metadata or {}), "discount": f"{line_discount:.2f}"},
            )
        )
    return [line for line in result if line.amount > 0]


def _ensure_lines_total(lines: list[FiscalLine], expected: Decimal) -> list[FiscalLine]:
    expected = money(expected)
    actual = sum((line.amount for line in lines), Decimal("0.00"))
    delta = money(expected - actual)
    if not lines or delta == 0:
        return lines

    last = lines[-1]
    adjusted = money(last.amount + delta)
    if adjusted <= 0:
        raise ValueError("Невозможно подготовить чек: сумма строк не сходится")
    lines[-1] = FiscalLine(
        name=last.name,
        quantity=last.quantity,
        unit_price=money(adjusted / last.quantity) if last.quantity else adjusted,
        amount=adjusted,
        vat_code=last.vat_code,
        payment_subject=last.payment_subject,
        payment_mode=last.payment_mode,
        measure=last.measure,
        source_type=last.source_type,
        source_id=last.source_id,
        sku=last.sku,
        barcode=last.barcode,
        metadata={**(last.metadata or {}), "rounding_delta": f"{delta:.2f}"},
    )
    return lines


def _order_full_payment_lines(
    payment: Payment, expected_total: Decimal
) -> list[FiscalLine]:
    order = payment.order
    shop = order.shop
    payment_mode = payment.fiscal_payment_mode or FiscalPaymentMode.FULL_PAYMENT
    base_amount = money(
        order.final_cost if order.final_cost is not None else order.cost_estimate
    )

    lines = [
        _line(
            name=f"Ремонт {order.device}",
            amount=base_amount,
            vat_code=_default_vat(shop, FiscalPaymentSubject.SERVICE),
            payment_subject=FiscalPaymentSubject.SERVICE,
            payment_mode=payment_mode,
            measure=FiscalMeasure.SERVICE,
            source_type="order_repair",
            source_id=order.id,
        )
    ]

    for order_service in order.orderservice_set.select_related("service"):
        service = order_service.service
        subject = service.fiscal_subject or FiscalPaymentSubject.SERVICE
        lines.append(
            _line(
                name=service.name,
                amount=money(order_service.total_price),
                quantity_value=Decimal(order_service.quantity),
                vat_code=_vat_for(service.fiscal_vat_code, shop, subject),
                payment_subject=subject,
                payment_mode=payment_mode,
                measure=service.fiscal_measure or FiscalMeasure.SERVICE,
                source_type="order_service",
                source_id=order_service.id,
            )
        )

    lines = _discounted_lines(lines, order.discount_total)
    return _ensure_lines_total(lines, expected_total)


def _order_prepayment_line(payment: Payment) -> list[FiscalLine]:
    order = payment.order
    return [
        _line(
            name=f"Предоплата по заказу {order.order_number}",
            amount=payment.amount,
            vat_code=_default_vat(order.shop, FiscalPaymentSubject.SERVICE),
            payment_subject=FiscalPaymentSubject.SERVICE,
            payment_mode=FiscalPaymentMode.PARTIAL_PREPAYMENT,
            measure=FiscalMeasure.SERVICE,
            source_type="order_prepayment",
            source_id=order.id,
        )
    ]


def _build_order_components(
    payment: Payment,
) -> tuple[list[FiscalLine], list[dict[str, str]], Decimal]:
    order = payment.order
    order_total = money(order.total_cost)
    payment_amount = money(payment.amount)
    if payment_amount <= 0:
        raise ValueError("Сумма платежа для чека должна быть больше нуля")

    prior_paid = money(order.prepayment)
    remaining_before_payment = max(Decimal("0.00"), money(order_total - prior_paid))
    payment_type = _payment_type(payment)

    if payment_amount == order_total or payment_amount >= remaining_before_payment:
        lines = _order_full_payment_lines(payment, order_total)
        prepaid_amount = max(Decimal("0.00"), money(order_total - payment_amount))
        prepaid_amount = min(prepaid_amount, prior_paid)
        payments = []
        if payment_amount > 0:
            payments.append({"type": payment_type, "amount": f"{payment_amount:.2f}"})
        if prepaid_amount > 0:
            payments.append(
                {"type": FiscalPaymentType.PREPAID, "amount": f"{prepaid_amount:.2f}"}
            )
        return lines, payments, order_total

    return (
        _order_prepayment_line(payment),
        [{"type": payment_type, "amount": f"{payment_amount:.2f}"}],
        payment_amount,
    )


def _build_retail_sale_components(
    payment: Payment,
) -> tuple[list[FiscalLine], list[dict[str, str]], Decimal]:
    sale = payment.retail_sale
    payment_amount = money(payment.amount)
    sale_total = money(sale.total_amount)
    if payment_amount != sale_total:
        raise ValueError(
            "Для розничной продажи фискальный чек должен совпадать с итогом продажи"
        )

    lines: list[FiscalLine] = []
    for sale_item in sale.items.select_related("item"):
        item = sale_item.item
        subject = item.fiscal_subject or (
            FiscalPaymentSubject.SERVICE
            if item.item_type == item.ItemType.SERVICE
            else FiscalPaymentSubject.COMMODITY
        )
        lines.append(
            _line(
                name=item.name,
                amount=money(sale_item.total_price),
                quantity_value=Decimal(sale_item.quantity),
                vat_code=_vat_for(item.fiscal_vat_code, sale.shop, subject),
                payment_subject=subject,
                payment_mode=payment.fiscal_payment_mode
                or FiscalPaymentMode.FULL_PAYMENT,
                measure=item.fiscal_measure or FiscalMeasure.PIECE,
                source_type="retail_sale_item",
                source_id=sale_item.id,
                sku=item.sku,
                barcode=item.barcode,
            )
        )

    lines = _discounted_lines(lines, sale.discount_amount)
    lines = _ensure_lines_total(lines, payment_amount)
    return (
        lines,
        [{"type": _payment_type(payment), "amount": f"{payment_amount:.2f}"}],
        payment_amount,
    )


def build_payment_receipt_snapshot(
    payment: Payment, *, require_customer_contact: bool = False
) -> dict[str, Any]:
    shop = _payment_shop(payment)
    if not shop:
        raise ValueError("Платеж не привязан к филиалу для фискализации")

    if (
        payment.payment_type != Payment.PaymentType.INCOME
        or not payment.fiscal_required
    ):
        raise ValueError("Фискальный чек для этого платежа не требуется")

    if payment.order_id:
        lines, payments, receipt_total = _build_order_components(payment)
    elif payment.retail_sale_id:
        lines, payments, receipt_total = _build_retail_sale_components(payment)
    else:
        raise ValueError("Платеж должен быть привязан к заказу или розничной продаже")

    email, phone = _customer_contact(payment)
    if require_customer_contact and not (email or phone):
        raise ValueError("Для онлайн-чека нужен email или телефон клиента")

    total = sum((line.amount for line in lines), Decimal("0.00"))
    payments_total = sum((money(item["amount"]) for item in payments), Decimal("0.00"))
    if money(total) != money(receipt_total) or money(payments_total) != money(total):
        raise ValueError("Сумма фискального чека не сходится с оплатами")

    return {
        "payment_id": payment.id,
        "payment_number": payment.payment_number,
        "total_amount": f"{money(total):.2f}",
        "received_amount": f"{money(payment.amount):.2f}",
        "currency": shop.currency or "RUB",
        "taxation_system": _shop_taxation_system(shop),
        "payment_type": _payment_type(payment),
        "customer": {"email": email, "phone": phone},
        "payments": payments,
        "items": [
            {
                "name": line.name,
                "quantity": f"{line.quantity:.3f}",
                "unit_price": f"{line.unit_price:.2f}",
                "amount": f"{line.amount:.2f}",
                "vat_code": line.vat_code,
                "payment_subject": line.payment_subject,
                "payment_mode": line.payment_mode,
                "measure": line.measure,
                "source_type": line.source_type,
                "source_id": line.source_id,
                "sku": line.sku,
                "barcode": line.barcode,
                "metadata": line.metadata or {},
            }
            for line in lines
        ],
    }


@transaction.atomic
def create_or_update_payment_receipt(payment: Payment) -> PaymentReceipt | None:
    shop = _payment_shop(payment)
    if not shop or not _shop_fiscal_enabled(shop):
        return None

    try:
        snapshot = build_payment_receipt_snapshot(payment)
    except ValueError as exc:
        receipt, _ = PaymentReceipt.objects.update_or_create(
            payment=payment,
            defaults={
                "status": PaymentReceipt.Status.FAILED,
                "total_amount": money(payment.amount),
                "received_amount": money(payment.amount),
                "taxation_system": _shop_taxation_system(shop),
                "currency": shop.currency or "RUB",
                "customer_email": "",
                "customer_phone": "",
                "normalized_snapshot": {},
                "error_message": str(exc),
            },
        )
        return receipt

    receipt, _ = PaymentReceipt.objects.update_or_create(
        payment=payment,
        defaults={
            "status": PaymentReceipt.Status.DRAFT,
            "taxation_system": snapshot["taxation_system"],
            "payment_type": snapshot["payment_type"],
            "total_amount": money(snapshot["total_amount"]),
            "received_amount": money(snapshot["received_amount"]),
            "currency": snapshot["currency"],
            "customer_email": snapshot["customer"]["email"],
            "customer_phone": snapshot["customer"]["phone"],
            "normalized_snapshot": snapshot,
            "error_message": "",
        },
    )
    receipt.items.all().delete()
    PaymentReceiptItem.objects.bulk_create(
        [
            PaymentReceiptItem(
                receipt=receipt,
                position=index,
                source_type=item["source_type"],
                source_id=item["source_id"],
                name=item["name"],
                quantity=Decimal(item["quantity"]),
                unit_price=money(item["unit_price"]),
                amount=money(item["amount"]),
                vat_code=item["vat_code"],
                payment_subject=item["payment_subject"],
                payment_mode=item["payment_mode"],
                measure=item["measure"],
                sku=item["sku"],
                barcode=item["barcode"],
                metadata=item["metadata"],
            )
            for index, item in enumerate(snapshot["items"], start=1)
        ]
    )
    return receipt


YOOKASSA_TAXATION = {
    FiscalTaxationSystem.OSN: 1,
    FiscalTaxationSystem.USN_INCOME: 2,
    FiscalTaxationSystem.USN_INCOME_OUTCOME: 3,
    FiscalTaxationSystem.ENVD: 4,
    FiscalTaxationSystem.ESN: 5,
    FiscalTaxationSystem.PATENT: 6,
}

YOOKASSA_VAT = {
    FiscalVatCode.NONE: 1,
    FiscalVatCode.VAT0: 2,
    FiscalVatCode.VAT10: 3,
    FiscalVatCode.VAT20: 4,
    FiscalVatCode.VAT110: 5,
    FiscalVatCode.VAT120: 6,
    FiscalVatCode.VAT5: 7,
    FiscalVatCode.VAT7: 8,
    FiscalVatCode.VAT105: 9,
    FiscalVatCode.VAT107: 10,
    FiscalVatCode.VAT22: 11,
    FiscalVatCode.VAT122: 12,
}

YOOKASSA_PAYMENT_SUBJECT = {
    FiscalPaymentSubject.COMMODITY: "commodity",
    FiscalPaymentSubject.SERVICE: "service",
    FiscalPaymentSubject.WORK: "job",
    FiscalPaymentSubject.PAYMENT: "payment",
}

YOOKASSA_PAYMENT_MODE = {
    FiscalPaymentMode.FULL_PREPAYMENT: "full_prepayment",
    FiscalPaymentMode.FULL_PAYMENT: "full_payment",
}

YOOKASSA_MEASURE = {
    FiscalMeasure.PIECE: "piece",
    FiscalMeasure.GRAM: "gram",
    FiscalMeasure.KILOGRAM: "kilogram",
    FiscalMeasure.TON: "ton",
    FiscalMeasure.CENTIMETER: "centimeter",
    FiscalMeasure.DECIMETER: "decimeter",
    FiscalMeasure.METER: "meter",
    FiscalMeasure.SQUARE_METER: "square_meter",
    FiscalMeasure.LITER: "liter",
    FiscalMeasure.DAY: "day",
    FiscalMeasure.HOUR: "hour",
    FiscalMeasure.SERVICE: "another",
}

TBANK_TAXATION = {
    FiscalTaxationSystem.OSN: "osn",
    FiscalTaxationSystem.USN_INCOME: "usn_income",
    FiscalTaxationSystem.USN_INCOME_OUTCOME: "usn_income_outcome",
    FiscalTaxationSystem.ENVD: "envd",
    FiscalTaxationSystem.ESN: "esn",
    FiscalTaxationSystem.PATENT: "patent",
}

TBANK_VAT = {
    FiscalVatCode.NONE: "none",
    FiscalVatCode.VAT0: "vat0",
    FiscalVatCode.VAT5: "vat5",
    FiscalVatCode.VAT7: "vat7",
    FiscalVatCode.VAT10: "vat10",
    FiscalVatCode.VAT20: "vat20",
    FiscalVatCode.VAT22: "vat22",
    FiscalVatCode.VAT105: "vat105",
    FiscalVatCode.VAT107: "vat107",
    FiscalVatCode.VAT110: "vat110",
    FiscalVatCode.VAT120: "vat120",
    FiscalVatCode.VAT122: "vat122",
}

TBANK_PAYMENT_METHOD = {
    FiscalPaymentMode.FULL_PREPAYMENT: "full_prepayment",
    FiscalPaymentMode.PARTIAL_PREPAYMENT: "prepayment",
    FiscalPaymentMode.ADVANCE: "advance",
    FiscalPaymentMode.FULL_PAYMENT: "full_payment",
    FiscalPaymentMode.PARTIAL_PAYMENT: "partial_payment",
    FiscalPaymentMode.CREDIT: "credit",
    FiscalPaymentMode.CREDIT_PAYMENT: "credit_payment",
}

TBANK_PAYMENT_OBJECT = {
    FiscalPaymentSubject.COMMODITY: "commodity",
    FiscalPaymentSubject.SERVICE: "service",
    FiscalPaymentSubject.WORK: "job",
    FiscalPaymentSubject.PAYMENT: "payment",
}

TBANK_MEASURE = {
    FiscalMeasure.PIECE: "шт",
    FiscalMeasure.GRAM: "г",
    FiscalMeasure.KILOGRAM: "кг",
    FiscalMeasure.TON: "т",
    FiscalMeasure.CENTIMETER: "см",
    FiscalMeasure.DECIMETER: "дм",
    FiscalMeasure.METER: "м",
    FiscalMeasure.SQUARE_METER: "кв. м",
    FiscalMeasure.LITER: "л",
    FiscalMeasure.DAY: "сут",
    FiscalMeasure.HOUR: "ч",
    FiscalMeasure.SERVICE: "-",
}

SBER_VAT = {
    FiscalVatCode.NONE: 0,
    FiscalVatCode.VAT0: 1,
    FiscalVatCode.VAT10: 2,
    FiscalVatCode.VAT20: 3,
    FiscalVatCode.VAT110: 4,
    FiscalVatCode.VAT120: 5,
    FiscalVatCode.VAT22: 11,
    FiscalVatCode.VAT122: 12,
}

SBER_PAYMENT_METHOD = {
    FiscalPaymentMode.FULL_PREPAYMENT: 1,
    FiscalPaymentMode.PARTIAL_PREPAYMENT: 2,
    FiscalPaymentMode.ADVANCE: 3,
    FiscalPaymentMode.FULL_PAYMENT: 4,
    FiscalPaymentMode.PARTIAL_PAYMENT: 5,
    FiscalPaymentMode.CREDIT: 6,
    FiscalPaymentMode.CREDIT_PAYMENT: 7,
}

SBER_PAYMENT_OBJECT = {
    FiscalPaymentSubject.COMMODITY: 1,
    FiscalPaymentSubject.SERVICE: 4,
    FiscalPaymentSubject.WORK: 3,
    FiscalPaymentSubject.PAYMENT: 10,
}


def _require_supported(mapping: dict[str, Any], code: str, provider: str, field: str):
    if code not in mapping:
        raise ValueError(f"{provider} не поддерживает {field}={code}")
    return mapping[code]


def _kopecks(value: str | Decimal) -> int:
    return int((money(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def receipt_snapshot_to_yookassa(snapshot: dict[str, Any]) -> dict[str, Any]:
    if money(snapshot["total_amount"]) != money(snapshot["received_amount"]):
        raise ValueError(
            "YooKassa receipt in payment request must match the charged amount; "
            "issue final-settlement KKM receipt separately"
        )
    customer = snapshot["customer"]
    receipt: dict[str, Any] = {
        "tax_system_code": _require_supported(
            YOOKASSA_TAXATION,
            snapshot["taxation_system"],
            "YooKassa",
            "taxation_system",
        ),
        "items": [],
    }
    if customer.get("email"):
        receipt["customer"] = {"email": customer["email"]}
    elif customer.get("phone"):
        receipt["customer"] = {"phone": customer["phone"]}

    for item in snapshot["items"]:
        receipt["items"].append(
            {
                "description": item["name"][:128],
                "quantity": item["quantity"],
                "amount": {
                    "value": item["amount"],
                    "currency": snapshot["currency"],
                },
                "vat_code": _require_supported(
                    YOOKASSA_VAT, item["vat_code"], "YooKassa", "vat_code"
                ),
                "payment_subject": _require_supported(
                    YOOKASSA_PAYMENT_SUBJECT,
                    item["payment_subject"],
                    "YooKassa",
                    "payment_subject",
                ),
                "payment_mode": _require_supported(
                    YOOKASSA_PAYMENT_MODE,
                    item["payment_mode"],
                    "YooKassa",
                    "payment_mode",
                ),
                "measure": _require_supported(
                    YOOKASSA_MEASURE, item["measure"], "YooKassa", "measure"
                ),
            }
        )
    return receipt


def receipt_snapshot_to_tbank(snapshot: dict[str, Any]) -> dict[str, Any]:
    if money(snapshot["total_amount"]) != money(snapshot["received_amount"]):
        raise ValueError(
            "T-Bank receipt in payment request must match the charged amount; "
            "issue final-settlement KKM receipt separately"
        )
    customer = snapshot["customer"]
    receipt: dict[str, Any] = {
        "Taxation": _require_supported(
            TBANK_TAXATION, snapshot["taxation_system"], "T-Bank", "taxation_system"
        ),
        "Items": [],
    }
    if customer.get("email"):
        receipt["Email"] = customer["email"]
    if customer.get("phone"):
        receipt["Phone"] = customer["phone"]

    for item in snapshot["items"]:
        receipt["Items"].append(
            {
                "Name": item["name"][:128],
                "Price": _kopecks(item["unit_price"]),
                "Quantity": item["quantity"],
                "Amount": _kopecks(item["amount"]),
                "Tax": _require_supported(
                    TBANK_VAT, item["vat_code"], "T-Bank", "vat_code"
                ),
                "PaymentMethod": _require_supported(
                    TBANK_PAYMENT_METHOD,
                    item["payment_mode"],
                    "T-Bank",
                    "payment_mode",
                ),
                "PaymentObject": _require_supported(
                    TBANK_PAYMENT_OBJECT,
                    item["payment_subject"],
                    "T-Bank",
                    "payment_subject",
                ),
                "MeasurementUnit": _require_supported(
                    TBANK_MEASURE, item["measure"], "T-Bank", "measure"
                ),
            }
        )
    return receipt


def receipt_snapshot_to_sber(snapshot: dict[str, Any]) -> dict[str, Any]:
    if money(snapshot["total_amount"]) != money(snapshot["received_amount"]):
        raise ValueError(
            "Sber receipt in payment request must match the charged amount; "
            "issue final-settlement KKM receipt separately"
        )
    items = []
    for position, item in enumerate(snapshot["items"], start=1):
        items.append(
            {
                "positionId": position,
                "name": item["name"][:128],
                "itemCode": item.get("sku") or f"item-{position}",
                "quantity": {
                    "value": item["quantity"],
                    "measure": item["measure"],
                },
                "itemPrice": _kopecks(item["unit_price"]),
                "itemAmount": _kopecks(item["amount"]),
                "tax": {
                    "taxType": _require_supported(
                        SBER_VAT, item["vat_code"], "Sber", "vat_code"
                    )
                },
                "itemAttributes": {
                    "attributes": [
                        {
                            "name": "paymentMethod",
                            "value": _require_supported(
                                SBER_PAYMENT_METHOD,
                                item["payment_mode"],
                                "Sber",
                                "payment_mode",
                            ),
                        },
                        {
                            "name": "paymentObject",
                            "value": _require_supported(
                                SBER_PAYMENT_OBJECT,
                                item["payment_subject"],
                                "Sber",
                                "payment_subject",
                            ),
                        },
                    ]
                },
            }
        )
    return {"cartItems": {"items": items}}
