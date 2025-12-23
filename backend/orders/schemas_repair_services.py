from decimal import Decimal
from typing import Optional

from ninja import Schema


class RepairServiceSchema(Schema):
    id: int
    code: str
    name: str
    device_type_id: Optional[int] = None
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    default_price: float
    avg_hours: float
    warranty_days: int
    diagnostics_required: bool
    notes: Optional[str] = None

    @staticmethod
    def resolve_default_price(obj):
        return float(obj.default_price)

    @staticmethod
    def resolve_avg_hours(obj):
        return float(obj.avg_hours)
