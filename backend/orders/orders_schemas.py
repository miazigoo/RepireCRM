from datetime import datetime

from ninja import Schema

from customers.customers_schemas import CustomerSchema
from promotions.schemas import OrderDiscountSchema
from Schemas.common import PaginationSchema


class DeviceBrandSchema(Schema):
    id: int
    name: str


class DeviceTypeSchema(Schema):
    id: int
    name: str
    icon: str | None = None


class DeviceModelSchema(Schema):
    id: int
    brand: DeviceBrandSchema
    device_type: DeviceTypeSchema
    name: str
    model_number: str | None = None
    release_year: int | None = None


class DeviceSchema(Schema):
    id: int
    model: DeviceModelSchema
    serial_number: str | None = None
    imei: str | None = None
    color: str | None = None
    storage_capacity: str | None = None
    specifications: dict | None = None


class DeviceCreateSchema(Schema):
    model_id: int
    serial_number: str | None = None
    imei: str | None = None
    color: str | None = None
    storage_capacity: str | None = None
    specifications: dict | None = None


class DeviceModelCreateSchema(Schema):
    brand_name: str
    name: str
    device_type_name: str | None = "Смартфон"
    model_number: str | None = None
    release_year: int | None = None


class AdditionalServiceSchema(Schema):
    id: int
    name: str
    category: str
    description: str | None = None
    price: float
    is_active: bool = True
    shop_ids: list[int] = []

    @staticmethod
    def resolve_price(obj):
        return float(obj.price)

    @staticmethod
    def resolve_shop_ids(obj):
        return list(obj.shops.values_list("id", flat=True))


class AdditionalServiceCreateSchema(Schema):
    name: str
    category: str = "other"
    description: str | None = None
    price: float
    is_active: bool = True
    shop_ids: list[int] = []


class AdditionalServiceUpdateSchema(Schema):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = None
    is_active: bool | None = None
    shop_ids: list[int] | None = None


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
    accessories: str | None = None
    device_condition: str | None = None
    cost_estimate: float
    priority: str | None = "normal"
    estimated_completion: datetime | None = None
    additional_services: list[dict] | None = None  # [{"service_id": 1, "quantity": 1}]


class OrderUpdateSchema(Schema):
    status: str | None = None
    diagnosis: str | None = None
    work_description: str | None = None
    final_cost: float | None = None
    prepayment: float | None = None
    assigned_to_id: int | None = None
    estimated_completion: datetime | None = None
    notes: str | None = None
    status_comment: str | None = None


class OrderStatusHistorySchema(Schema):
    id: int
    old_status: str | None = None
    new_status: str
    comment: str | None = None
    changed_by_name: str | None = None
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
    actor_name: str | None = None
    created_at: datetime

    @staticmethod
    def resolve_actor_name(obj):
        if not obj.actor:
            return None
        return obj.actor.full_name


class RepairStageSchema(Schema):
    id: int
    title: str
    description: str | None = None
    photo_url: str | None = None
    customer_visible: bool
    position: int
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_created_by_name(obj):
        if not obj.created_by:
            return None
        return obj.created_by.full_name


class RepairStageUpdateSchema(Schema):
    title: str | None = None
    description: str | None = None
    customer_visible: bool | None = None


class OrderApprovalSchema(Schema):
    id: int
    title: str
    description: str | None = None
    amount: float
    status: str
    status_display: str
    customer_comment: str | None = None
    requested_by_name: str | None = None
    decided_at: datetime | None = None
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
    description: str | None = None
    amount: float


class WarrantyCaseCreateSchema(Schema):
    reason: str
    problem_description: str | None = None
    priority: str | None = "high"
    estimated_completion: datetime | None = None


class WarrantyOrderSummarySchema(Schema):
    id: int
    order_number: str
    status: str
    priority: str
    problem_description: str
    created_at: datetime
    completed_at: datetime | None = None
    warranty_reason: str | None = None


class OrderSchema(Schema):
    id: int
    order_number: str
    customer: CustomerSchema
    device: DeviceSchema
    status: str
    priority: str
    problem_description: str
    diagnosis: str | None = None
    work_description: str | None = None
    accessories: str | None = None
    device_condition: str | None = None
    cost_estimate: float
    final_cost: float | None = None
    prepayment: float
    subtotal_before_discount: float
    discount_total: float
    total_cost: float
    remaining_payment: float
    created_at: datetime
    updated_at: datetime
    estimated_completion: datetime | None = None
    completed_at: datetime | None = None
    additional_services: list[OrderServiceSchema]
    discounts: list[OrderDiscountSchema] = []
    notes: str | None = None
    warranty_days: int
    warranty_until: datetime | None = None
    warranty_active: bool = False
    is_warranty_case: bool = False
    warranty_parent_order_id: int | None = None
    warranty_parent_order_number: str | None = None
    warranty_reason: str | None = None
    warranty_resolution: str | None = None
    warranty_cases_count: int = 0

    @staticmethod
    def resolve_additional_services(obj):
        return obj.orderservice_set.all()

    @staticmethod
    def resolve_cost_estimate(obj):
        return float(obj.cost_estimate)

    @staticmethod
    def resolve_final_cost(obj):
        return float(obj.final_cost) if obj.final_cost is not None else None

    @staticmethod
    def resolve_prepayment(obj):
        return float(obj.prepayment)

    @staticmethod
    def resolve_subtotal_before_discount(obj):
        return float(obj.subtotal_before_discount)

    @staticmethod
    def resolve_discount_total(obj):
        return float(obj.discount_total)

    @staticmethod
    def resolve_total_cost(obj):
        return float(obj.total_cost)

    @staticmethod
    def resolve_remaining_payment(obj):
        return float(obj.remaining_payment)

    @staticmethod
    def resolve_discounts(obj):
        return obj.discounts.all()

    @staticmethod
    def resolve_warranty_active(obj):
        return bool(obj.warranty_active)

    @staticmethod
    def resolve_warranty_parent_order_id(obj):
        return obj.warranty_parent_id

    @staticmethod
    def resolve_warranty_parent_order_number(obj):
        if not obj.warranty_parent:
            return None
        return obj.warranty_parent.order_number

    @staticmethod
    def resolve_warranty_cases_count(obj):
        return obj.warranty_cases.count()


class OrderListSchema(Schema):
    orders: list[OrderSchema]
    pagination: PaginationSchema


class OrderFilterSchema(Schema):
    search: str | None = None
    status: str | None = None
    priority: str | None = None
    customer_id: int | None = None
    assigned_to_id: int | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    estimated_completion_from: datetime | None = None
    estimated_completion_to: datetime | None = None
