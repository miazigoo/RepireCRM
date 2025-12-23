from datetime import date, datetime
from typing import List, Optional

from ninja import Schema

from Schemas.common import PaginationSchema


class CustomerCreateSchema(Schema):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    source: Optional[str] = None
    source_details: Optional[str] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    preferred_channel: Optional[str] = None  # "email" | "sms"
    marketing_consent: Optional[bool] = False


class CustomerUpdateSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    source_details: Optional[str] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    preferred_channel: Optional[str] = None
    marketing_consent: Optional[bool] = None


class CustomerSchema(Schema):
    id: int
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    source: Optional[str] = None
    source_details: Optional[str] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    orders_count: int
    total_spent: float
    created_at: datetime
    updated_at: datetime
    preferred_channel: Optional[str] = None
    marketing_consent: bool

    @staticmethod
    def resolve_total_spent(obj):
        return float(obj.total_spent)


class CustomerListSchema(Schema):
    customers: List[CustomerSchema]
    pagination: PaginationSchema


class CustomerFilterSchema(Schema):
    search: Optional[str] = None
    source: Optional[str] = None
    created_from: Optional[date] = None
    created_to: Optional[date] = None
    has_orders: Optional[bool] = None
