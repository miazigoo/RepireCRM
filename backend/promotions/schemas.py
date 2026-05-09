from datetime import datetime
from typing import List, Optional

from ninja import Schema


class PromotionSchema(Schema):
    id: int
    name: str
    description: Optional[str] = None
    discount_type: str
    value: float
    max_discount_amount: Optional[float] = None
    min_order_amount: float
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool
    auto_apply: bool
    stackable: bool
    usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None
    shop_ids: List[int] = []
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
    description: Optional[str] = None
    discount_type: str = "percent"
    value: float
    max_discount_amount: Optional[float] = None
    min_order_amount: float = 0
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool = True
    auto_apply: bool = False
    stackable: bool = False
    usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None
    shop_ids: List[int] = []


class PromotionUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    value: Optional[float] = None
    max_discount_amount: Optional[float] = None
    min_order_amount: Optional[float] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    auto_apply: Optional[bool] = None
    stackable: Optional[bool] = None
    usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None
    shop_ids: Optional[List[int]] = None


class PromoCodeSchema(Schema):
    id: int
    promotion_id: int
    promotion_name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None
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
    description: Optional[str] = None
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None


class PromoCodeUpdateSchema(Schema):
    promotion_id: Optional[int] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None


class PromoCodeValidateSchema(Schema):
    code: str
    order_id: Optional[int] = None
    customer_id: Optional[int] = None
    subtotal: Optional[float] = None


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
    promotion_id: Optional[int] = None
    promotion_name: Optional[str] = None
    promo_code_id: Optional[int] = None
    promo_code: Optional[str] = None
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
    code: Optional[str] = None
    promotion_id: Optional[int] = None
    promotion_name: Optional[str] = None
    subtotal: float = 0
    discount_amount: float = 0
    total_after_discount: float = 0
