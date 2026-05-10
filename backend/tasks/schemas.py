from datetime import datetime
from typing import Any

from ninja import Schema


class TaskCreateSchema(Schema):
    # Обязательные
    title: str
    description: str
    assignment_type: str  # "individual" | "shop" | "all_shops" | "role"

    # Необязательные
    category_id: int | None = None
    priority: str | None = "normal"  # "low" | "normal" | "high" | "urgent"
    kind: str | None = "regular"  # "regular" | "urgent" | "global" | "planned"
    status: str = (
        "pending"  # "pending" | "in_progress" | "completed" | "cancelled" | "overdue"
    )
    substatus: str | None = "new"

    assigned_to_id: int | None = None
    assigned_shop_id: int | None = None
    assigned_role_id: int | None = None

    related_order_id: int | None = None
    related_customer_id: int | None = None

    due_date: datetime | None = None
    estimated_hours: float | None = None
    is_paid: bool | None = False
    payment_amount: float | None = 0

    attachments: list[dict[str, Any]] | None = None

    # Повторяющиеся задачи (если нужно)
    is_recurring: bool | None = False
    recurrence_pattern: dict[str, Any] | None = None


class TaskUpdateSchema(Schema):
    # Все поля опциональны
    title: str | None = None
    description: str | None = None

    category_id: int | None = None
    priority: str | None = None
    kind: str | None = None
    status: str | None = None
    substatus: str | None = None

    assignment_type: str | None = None
    assigned_to_id: int | None = None
    assigned_shop_id: int | None = None
    assigned_role_id: int | None = None

    related_order_id: int | None = None
    related_customer_id: int | None = None

    due_date: datetime | None = None
    estimated_hours: float | None = None
    actual_hours: float | None = None
    is_paid: bool | None = None
    payment_amount: float | None = None

    progress_percent: int | None = None
    attachments: list[dict[str, Any]] | None = None

    is_recurring: bool | None = None
    recurrence_pattern: dict[str, Any] | None = None


class TaskSchema(Schema):
    id: int
    title: str
    description: str

    status: str
    priority: str
    kind: str
    substatus: str
    assignment_type: str

    category_id: int | None = None
    category_name: str | None = None

    assigned_to_id: int | None = None
    assigned_to_name: str | None = None
    assigned_to: str | None = None

    assigned_shop_id: int | None = None
    assigned_shop_name: str | None = None
    assigned_shop: str | None = None

    assigned_role_id: int | None = None
    assigned_role_name: str | None = None

    related_order_id: int | None = None
    related_customer_id: int | None = None

    due_date: datetime | None = None
    estimated_hours: float | None = None
    actual_hours: float | None = None
    is_paid: bool
    payment_amount: float

    progress_percent: int
    attachments: list[dict]
    created_by: str | None = None

    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    is_overdue: bool

    @staticmethod
    def resolve_category_name(obj):
        return obj.category.name if obj.category else None

    @staticmethod
    def resolve_assigned_to_name(obj):
        if obj.assigned_to:
            full = obj.assigned_to.get_full_name()
            return full if full.strip() else obj.assigned_to.username
        return None

    @staticmethod
    def resolve_assigned_to(obj):
        return TaskSchema.resolve_assigned_to_name(obj)

    @staticmethod
    def resolve_assigned_shop_name(obj):
        return obj.assigned_shop.name if obj.assigned_shop else None

    @staticmethod
    def resolve_assigned_shop(obj):
        return TaskSchema.resolve_assigned_shop_name(obj)

    @staticmethod
    def resolve_assigned_role_name(obj):
        return obj.assigned_role.name if obj.assigned_role else None

    @staticmethod
    def resolve_estimated_hours(obj):
        return float(obj.estimated_hours) if obj.estimated_hours is not None else None

    @staticmethod
    def resolve_actual_hours(obj):
        return float(obj.actual_hours) if obj.actual_hours is not None else None

    @staticmethod
    def resolve_payment_amount(obj):
        return float(obj.payment_amount or 0)

    @staticmethod
    def resolve_attachments(obj):
        return obj.attachments or []

    @staticmethod
    def resolve_is_overdue(obj):
        return bool(obj.is_overdue)

    @staticmethod
    def resolve_created_by(obj):
        if not obj.created_by:
            return None
        full = obj.created_by.get_full_name()
        return full if full.strip() else obj.created_by.username
