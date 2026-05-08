from typing import Optional

from ninja import Schema


class OrganizationSchema(Schema):
    id: int
    name: str
    inn: Optional[str] = None
    kpp: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    bank_details: Optional[str] = None
    website: Optional[str] = None


class ShopSchema(Schema):
    id: int
    name: str
    code: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    timezone: str
    currency: str
    tax_rate: float

    @staticmethod
    def resolve_tax_rate(obj):
        return float(obj.tax_rate or 0)


class ShopSettingsSchema(Schema):
    order_number_prefix: str
    auto_order_numbering: bool
    sms_notifications: bool
    email_notifications: bool
    work_hours_start: Optional[str] = None
    work_hours_end: Optional[str] = None
    work_days: str
    pos_barcode_enabled: bool
    organization_id: Optional[int] = None
    receipt_footer_text: Optional[str] = None

    @staticmethod
    def resolve_work_hours_start(obj):
        return obj.work_hours_start.strftime("%H:%M") if obj.work_hours_start else None

    @staticmethod
    def resolve_work_hours_end(obj):
        return obj.work_hours_end.strftime("%H:%M") if obj.work_hours_end else None


class SubscriptionPlanSchema(Schema):
    code: str
    name: str
    billing_period: str
    duration_days: int
    price: float

    @staticmethod
    def resolve_price(obj):
        return float(obj.price)


class SubscriptionChangeSchema(Schema):
    plan_code: str


class SubscriptionStatusSchema(Schema):
    organization_id: int
    organization_name: str
    plan: SubscriptionPlanSchema
    status: str
    status_display: str
    started_at: str
    expires_at: str
    remaining_days: int
    remaining_percent: int
    color_bucket: int
    color_hex: str
    is_expired: bool
