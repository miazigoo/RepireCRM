from datetime import datetime

from ninja import Schema


class LoyaltyProgramSchema(Schema):
    id: int
    name: str
    program_type: str
    description: str | None = None
    earn_rate: float
    min_order_amount: float
    min_redeem_points: int
    max_redeem_percent: float
    point_value: float
    points_expire_days: int | None = None
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
    order_id: int | None = None
    description: str
    created_at: datetime
    expires_at: datetime | None = None


class LoyaltyRewardSchema(Schema):
    id: int
    name: str
    reward_type: str
    description: str
    required_points: int
    required_tier: str | None = None
    required_orders_count: int
    discount_percent: float | None = None
    bonus_points: int | None = None
    is_active: bool
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    usage_limit: int | None = None

    @staticmethod
    def resolve_discount_percent(obj):
        return float(obj.discount_percent) if obj.discount_percent else None


class CustomerRewardSchema(Schema):
    id: int
    reward: LoyaltyRewardSchema
    order_id: int | None = None
    received_at: datetime
    used_at: datetime | None = None
    is_used: bool


class RedeemPointsSchema(Schema):
    customer_id: int
    order_id: int
    points: int
    description: str | None = ""
