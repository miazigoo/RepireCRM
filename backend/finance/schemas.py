from datetime import datetime

from ninja import Schema


class PaymentMethodSchema(Schema):
    id: int
    name: str
    code: str
    is_cash: bool


class CreateSalePaymentRequest(Schema):
    payment_method_id: int
    cash_register_id: int | None = None
    amount: float
    description: str | None = None


class PaymentSchema(Schema):
    id: int
    payment_number: str
    amount: float
    status: str
    payment_date: datetime
