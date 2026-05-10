from ninja import Schema


class RepairServiceSchema(Schema):
    id: int
    code: str
    name: str
    device_type_id: int | None = None
    brand_id: int | None = None
    model_id: int | None = None
    default_price: float
    avg_hours: float
    warranty_days: int
    diagnostics_required: bool
    notes: str | None = None

    @staticmethod
    def resolve_default_price(obj):
        return float(obj.default_price)

    @staticmethod
    def resolve_avg_hours(obj):
        return float(obj.avg_hours)
