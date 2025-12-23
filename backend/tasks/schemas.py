from datetime import datetime
from typing import Any, Dict, List, Optional

from ninja import Schema


class TaskCreateSchema(Schema):
    # Обязательные
    title: str
    description: str
    assignment_type: str  # "individual" | "shop" | "all_shops" | "role"

    # Необязательные
    category_id: Optional[int] = None
    priority: Optional[str] = "normal"  # "low" | "normal" | "high" | "urgent"
    status: Optional[
        str
    ] = "pending"  # "pending" | "in_progress" | "completed" | "cancelled" | "overdue"

    assigned_to_id: Optional[int] = None
    assigned_shop_id: Optional[int] = None
    assigned_role_id: Optional[int] = None

    related_order_id: Optional[int] = None
    related_customer_id: Optional[int] = None

    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None

    attachments: Optional[List[Dict[str, Any]]] = None

    # Повторяющиеся задачи (если нужно)
    is_recurring: Optional[bool] = False
    recurrence_pattern: Optional[Dict[str, Any]] = None


class TaskUpdateSchema(Schema):
    # Все поля опциональны
    title: Optional[str] = None
    description: Optional[str] = None

    category_id: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None

    assignment_type: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_shop_id: Optional[int] = None
    assigned_role_id: Optional[int] = None

    related_order_id: Optional[int] = None
    related_customer_id: Optional[int] = None

    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

    progress_percent: Optional[int] = None
    attachments: Optional[List[Dict[str, Any]]] = None

    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[Dict[str, Any]] = None


class TaskSchema(Schema):
    id: int
    title: str
    description: str

    status: str
    priority: str
    assignment_type: str

    category_id: Optional[int] = None
    category_name: Optional[str] = None

    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None

    assigned_shop_id: Optional[int] = None
    assigned_shop_name: Optional[str] = None

    assigned_role_id: Optional[int] = None
    assigned_role_name: Optional[str] = None

    related_order_id: Optional[int] = None
    related_customer_id: Optional[int] = None

    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

    progress_percent: int
    attachments: List[dict]

    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

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
    def resolve_assigned_shop_name(obj):
        return obj.assigned_shop.name if obj.assigned_shop else None

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
    def resolve_attachments(obj):
        return obj.attachments or []

    @staticmethod
    def resolve_is_overdue(obj):
        return bool(obj.is_overdue)
