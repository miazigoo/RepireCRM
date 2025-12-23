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
