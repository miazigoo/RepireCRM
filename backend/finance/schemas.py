from datetime import datetime
from typing import Optional

from ninja import Schema


class PaymentMethodSchema(Schema):
    id: int
    name: str
    code: str
    is_cash: bool


class CreateSalePaymentRequest(Schema):
    payment_method_id: int
    cash_register_id: Optional[int] = None
    amount: float
    description: Optional[str] = None


class PaymentSchema(Schema):
    id: int
    payment_number: str
    amount: float
    status: str
    payment_date: datetime
