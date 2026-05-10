from ninja import Schema


class OrganizationSchema(Schema):
    id: int
    name: str
    inn: str | None = None
    kpp: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    bank_details: str | None = None
    website: str | None = None


class ShopSchema(Schema):
    id: int
    name: str
    code: str
    city: str = ""
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool
    timezone: str
    currency: str
    tax_rate: float

    @staticmethod
    def resolve_latitude(obj):
        return float(obj.latitude) if obj.latitude is not None else None

    @staticmethod
    def resolve_longitude(obj):
        return float(obj.longitude) if obj.longitude is not None else None

    @staticmethod
    def resolve_tax_rate(obj):
        return float(obj.tax_rate or 0)


class ShopSettingsSchema(Schema):
    order_number_prefix: str
    auto_order_numbering: bool
    sms_notifications: bool
    email_notifications: bool
    work_hours_start: str | None = None
    work_hours_end: str | None = None
    work_days: str
    pos_barcode_enabled: bool
    organization_id: int | None = None
    receipt_footer_text: str | None = None

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


class SubscriptionPaymentCreateSchema(Schema):
    plan_code: str
    payment_method_type: str = "bank_card"
    return_url: str | None = None


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
