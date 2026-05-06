from datetime import datetime
from typing import List, Optional

from ninja import Schema

from customers.customers_schemas import CustomerSchema
from Schemas.common import PaginationSchema


class DeviceBrandSchema(Schema):
    id: int
    name: str


class DeviceTypeSchema(Schema):
    id: int
    name: str
    icon: Optional[str] = None


class DeviceModelSchema(Schema):
    id: int
    brand: DeviceBrandSchema
    device_type: DeviceTypeSchema
    name: str
    model_number: Optional[str] = None
    release_year: Optional[int] = None


class DeviceSchema(Schema):
    id: int
    model: DeviceModelSchema
    serial_number: Optional[str] = None
    imei: Optional[str] = None
    color: Optional[str] = None
    storage_capacity: Optional[str] = None
    specifications: Optional[dict] = None


class DeviceCreateSchema(Schema):
    model_id: int
    serial_number: Optional[str] = None
    imei: Optional[str] = None
    color: Optional[str] = None
    storage_capacity: Optional[str] = None
    specifications: Optional[dict] = None


class DeviceModelCreateSchema(Schema):
    brand_name: str
    name: str
    device_type_name: Optional[str] = "Смартфон"
    model_number: Optional[str] = None
    release_year: Optional[int] = None


class AdditionalServiceSchema(Schema):
    id: int
    name: str
    category: str
    description: Optional[str] = None
    price: float

    @staticmethod
    def resolve_price(obj):
        return float(obj.price)


class OrderServiceSchema(Schema):
    service: AdditionalServiceSchema
    quantity: int
    price: float
    total_price: float

    @staticmethod
    def resolve_price(obj):
        return float(obj.price)

    @staticmethod
    def resolve_total_price(obj):
        return float(obj.total_price)


class OrderCreateSchema(Schema):
    customer_id: int
    device: DeviceCreateSchema
    problem_description: str
    accessories: Optional[str] = None
    device_condition: Optional[str] = None
    cost_estimate: float
    priority: Optional[str] = "normal"
    estimated_completion: Optional[datetime] = None
    additional_services: Optional[
        List[dict]
    ] = None  # [{"service_id": 1, "quantity": 1}]


class OrderUpdateSchema(Schema):
    status: Optional[str] = None
    diagnosis: Optional[str] = None
    work_description: Optional[str] = None
    final_cost: Optional[float] = None
    prepayment: Optional[float] = None
    assigned_to_id: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    notes: Optional[str] = None
    status_comment: Optional[str] = None


class OrderStatusHistorySchema(Schema):
    id: int
    old_status: Optional[str] = None
    new_status: str
    comment: Optional[str] = None
    changed_by_name: Optional[str] = None
    changed_at: datetime

    @staticmethod
    def resolve_changed_by_name(obj):
        if not obj.changed_by:
            return None
        return obj.changed_by.full_name


class OrderAuditLogSchema(Schema):
    id: int
    action: str
    message: str
    changes: dict
    actor_name: Optional[str] = None
    created_at: datetime

    @staticmethod
    def resolve_actor_name(obj):
        if not obj.actor:
            return None
        return obj.actor.full_name


class RepairStageSchema(Schema):
    id: int
    title: str
    description: Optional[str] = None
    photo_url: Optional[str] = None
    customer_visible: bool
    position: int
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_created_by_name(obj):
        if not obj.created_by:
            return None
        return obj.created_by.full_name


class RepairStageUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    customer_visible: Optional[bool] = None


class OrderApprovalSchema(Schema):
    id: int
    title: str
    description: Optional[str] = None
    amount: float
    status: str
    status_display: str
    customer_comment: Optional[str] = None
    requested_by_name: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_amount(obj):
        return float(obj.amount)

    @staticmethod
    def resolve_requested_by_name(obj):
        if not obj.requested_by:
            return None
        return obj.requested_by.full_name


class OrderApprovalCreateSchema(Schema):
    title: str
    description: Optional[str] = None
    amount: float


class OrderSchema(Schema):
    id: int
    order_number: str
    customer: CustomerSchema
    device: DeviceSchema
    status: str
    priority: str
    problem_description: str
    diagnosis: Optional[str] = None
    work_description: Optional[str] = None
    accessories: Optional[str] = None
    device_condition: Optional[str] = None
    cost_estimate: float
    final_cost: Optional[float] = None
    prepayment: float
    total_cost: float
    remaining_payment: float
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    additional_services: List[OrderServiceSchema]
    notes: Optional[str] = None

    @staticmethod
    def resolve_additional_services(obj):
        return obj.orderservice_set.all()

    @staticmethod
    def resolve_cost_estimate(obj):
        return float(obj.cost_estimate)

    @staticmethod
    def resolve_final_cost(obj):
        return float(obj.final_cost) if obj.final_cost else None

    @staticmethod
    def resolve_prepayment(obj):
        return float(obj.prepayment)

    @staticmethod
    def resolve_total_cost(obj):
        return float(obj.total_cost)

    @staticmethod
    def resolve_remaining_payment(obj):
        return float(obj.remaining_payment)


class OrderListSchema(Schema):
    orders: List[OrderSchema]
    pagination: PaginationSchema


class OrderFilterSchema(Schema):
    search: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    customer_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    estimated_completion_from: Optional[datetime] = None
    estimated_completion_to: Optional[datetime] = None
