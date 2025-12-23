from datetime import datetime
from typing import Dict, Optional

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
    action_url: Optional[str] = None
    created_at: datetime
    data: Optional[Dict] = None
