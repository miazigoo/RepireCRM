from datetime import datetime

from ninja import Schema


class PromotionSchema(Schema):
    id: int
    name: str
    description: str | None = None
    discount_type: str
    value: float
    max_discount_amount: float | None = None
    min_order_amount: float
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool
    auto_apply: bool
    stackable: bool
    usage_limit: int | None = None
    per_customer_limit: int | None = None
    shop_ids: list[int] = []
    used_count: int = 0
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_value(obj):
        return float(obj.value)

    @staticmethod
    def resolve_max_discount_amount(obj):
        return (
            float(obj.max_discount_amount)
            if obj.max_discount_amount is not None
            else None
        )

    @staticmethod
    def resolve_min_order_amount(obj):
        return float(obj.min_order_amount)

    @staticmethod
    def resolve_shop_ids(obj):
        return list(obj.shops.values_list("id", flat=True))

    @staticmethod
    def resolve_used_count(obj):
        return obj.used_count


class PromotionCreateSchema(Schema):
    name: str
    description: str | None = None
    discount_type: str = "percent"
    value: float
    max_discount_amount: float | None = None
    min_order_amount: float = 0
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True
    auto_apply: bool = False
    stackable: bool = False
    usage_limit: int | None = None
    per_customer_limit: int | None = None
    shop_ids: list[int] = []


class PromotionUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    discount_type: str | None = None
    value: float | None = None
    max_discount_amount: float | None = None
    min_order_amount: float | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None
    auto_apply: bool | None = None
    stackable: bool | None = None
    usage_limit: int | None = None
    per_customer_limit: int | None = None
    shop_ids: list[int] | None = None


class PromoCodeSchema(Schema):
    id: int
    promotion_id: int
    promotion_name: str
    code: str
    description: str | None = None
    is_active: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    per_customer_limit: int | None = None
    used_count: int = 0
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_promotion_name(obj):
        return obj.promotion.name

    @staticmethod
    def resolve_used_count(obj):
        return obj.used_count


class PromoCodeCreateSchema(Schema):
    promotion_id: int
    code: str
    description: str | None = None
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    per_customer_limit: int | None = None


class PromoCodeUpdateSchema(Schema):
    promotion_id: int | None = None
    code: str | None = None
    description: str | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    per_customer_limit: int | None = None


class PromoCodeValidateSchema(Schema):
    code: str
    order_id: int | None = None
    customer_id: int | None = None
    subtotal: float | None = None


class ApplyPromoCodeSchema(Schema):
    code: str


class ManualDiscountCreateSchema(Schema):
    label: str = "Ручная скидка"
    amount: float


class OrderDiscountSchema(Schema):
    id: int
    source: str
    label: str
    amount: float
    promotion_id: int | None = None
    promotion_name: str | None = None
    promo_code_id: int | None = None
    promo_code: str | None = None
    created_at: datetime

    @staticmethod
    def resolve_amount(obj):
        return float(obj.amount)

    @staticmethod
    def resolve_promotion_name(obj):
        return obj.promotion.name if obj.promotion else None

    @staticmethod
    def resolve_promo_code(obj):
        return obj.promo_code.code if obj.promo_code else None


class DiscountQuoteSchema(Schema):
    valid: bool
    message: str
    code: str | None = None
    promotion_id: int | None = None
    promotion_name: str | None = None
    subtotal: float = 0
    discount_amount: float = 0
    total_after_discount: float = 0
