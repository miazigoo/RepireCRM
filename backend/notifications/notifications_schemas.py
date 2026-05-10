from datetime import datetime

from ninja import Schema


class NotificationSchema(Schema):
    id: int
    title: str
    message: str
    priority: str
    # типы и визуальные поля
    type: str
    icon: str
    color: str
    action_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    data: dict | None = None

    @staticmethod
    def resolve_type(obj):
        return obj.notification_type.code

    @staticmethod
    def resolve_icon(obj):
        return obj.notification_type.icon

    @staticmethod
    def resolve_color(obj):
        return obj.notification_type.color
