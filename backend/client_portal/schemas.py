from datetime import datetime
from typing import Optional

from ninja import Schema


class PortalCustomerSchema(Schema):
    id: int
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None


class PortalRegisterSchema(Schema):
    first_name: str
    last_name: str
    phone: str
    password: str
    email: Optional[str] = None
    marketing_consent: bool = False


class PortalLoginSchema(Schema):
    phone: str
    password: str


class PortalTokenSchema(Schema):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    customer: PortalCustomerSchema


class PortalOrderCreateSchema(Schema):
    device_type: str
    brand: str
    model_name: str
    problem_description: str
    serial_number: Optional[str] = None
    imei: Optional[str] = None
    color: Optional[str] = None
    storage_capacity: Optional[str] = None
    accessories: Optional[str] = None
    device_condition: Optional[str] = None
    cost_estimate: float = 0


class PortalOrderSchema(Schema):
    id: int
    order_number: str
    status: str
    status_display: str
    priority: str
    device_title: str
    problem_description: str
    diagnosis: Optional[str] = None
    work_description: Optional[str] = None
    cost_estimate: float
    final_cost: Optional[float] = None
    remaining_payment: float
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None


class PortalErrorSchema(Schema):
    error: str
    details: Optional[dict] = None
