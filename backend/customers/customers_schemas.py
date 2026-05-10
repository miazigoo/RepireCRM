from datetime import date, datetime

from ninja import Schema

from Schemas.common import PaginationSchema


class CustomerCreateSchema(Schema):
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str
    email: str | None = None
    source: str | None = None
    source_details: str | None = None
    birth_date: date | None = None
    notes: str | None = None
    preferred_channel: str | None = None  # "email" | "sms"
    marketing_consent: bool | None = False


class CustomerUpdateSchema(Schema):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    source_details: str | None = None
    birth_date: date | None = None
    notes: str | None = None
    preferred_channel: str | None = None
    marketing_consent: bool | None = None


class CustomerSchema(Schema):
    id: int
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str
    email: str | None = None
    source: str | None = None
    source_details: str | None = None
    birth_date: date | None = None
    notes: str | None = None
    orders_count: int
    total_spent: float
    created_at: datetime
    updated_at: datetime
    preferred_channel: str | None = None
    marketing_consent: bool

    @staticmethod
    def resolve_phone(obj):
        return str(obj.phone)

    @staticmethod
    def resolve_total_spent(obj):
        return float(obj.total_spent)


class CustomerListSchema(Schema):
    customers: list[CustomerSchema]
    pagination: PaginationSchema


class CustomerFilterSchema(Schema):
    search: str | None = None
    source: str | None = None
    created_from: date | None = None
    created_to: date | None = None
    has_orders: bool | None = None
