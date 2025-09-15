
from ninja import Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class LoyaltyProgramSchema(Schema):
    id: int
    name: str
    program_type: str
    description: Optional[str] = None
    earn_rate: float
    min_order_amount: float
    min_redeem_points: int
    max_redeem_percent: float
    point_value: float
    points_expire_days: Optional[int] = None
    is_active: bool

    @staticmethod
    def resolve_earn_rate(obj):
        return float(obj.earn_rate)

    @staticmethod
    def resolve_min_order_amount(obj):
        return float(obj.min_order_amount)

    @staticmethod
    def resolve_max_redeem_percent(obj):
        return float(obj.max_redeem_percent)

    @staticmethod
    def resolve_point_value(obj):
        return float(obj.point_value)


class CustomerLoyaltySchema(Schema):
    id: int
    customer_id: int
    program: LoyaltyProgramSchema
    total_points: int
    available_points: int
    used_points: int
    tier_level: str
    tier_points_threshold: int
    total_spent: float
    orders_count: int
    joined_at: datetime
    last_activity: datetime

    @staticmethod
    def resolve_total_spent(obj):
        return float(obj.total_spent)


class PointsTransactionSchema(Schema):
    id: int
    transaction_type: str
    points: int
    order_id: Optional[int] = None
    description: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class LoyaltyRewardSchema(Schema):
    id: int
    name: str
    reward_type: str
    description: str
    required_points: int
    required_tier: Optional[str] = None
    required_orders_count: int
    discount_percent: Optional[float] = None
    bonus_points: Optional[int] = None
    is_active: bool
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    usage_limit: Optional[int] = None

    @staticmethod
    def resolve_discount_percent(obj):
        return float(obj.discount_percent) if obj.discount_percent else None


class CustomerRewardSchema(Schema):
    id: int
    reward: LoyaltyRewardSchema
    order_id: Optional[int] = None
    received_at: datetime
    used_at: Optional[datetime] = None
    is_used: bool


class RedeemPointsSchema(Schema):
    customer_id: int
    order_id: int
    points: int
    description: Optional[str] = ""
