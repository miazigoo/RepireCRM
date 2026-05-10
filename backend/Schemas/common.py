from ninja import Schema


class MessageSchema(Schema):
    message: str
    success: bool = True


class ErrorSchema(Schema):
    error: str
    details: dict | None = None


class PaginationSchema(Schema):
    page: int = 1
    page_size: int = 20
    total: int
    total_pages: int


class ShopSchema(Schema):
    id: int
    name: str
    code: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool
    timezone: str
    currency: str


class RoleSchema(Schema):
    id: int
    name: str
    code: str
    description: str | None = None
    permission_codes: list[str] = []

    @staticmethod
    def resolve_permission_codes(obj):
        return list(obj.permissions.values_list("codename", flat=True))


class UserSchema(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    email: str
    phone: str | None = None
    is_active: bool
    is_director: bool
    current_shop: ShopSchema | None = None
    available_shops: list[ShopSchema] = []
    avatar: str | None = None
    profile_status: str | None = None
    bio: str | None = None
    compensation_type: str = "fixed"
    fixed_order_payment: float = 0
    service_commission_percent: float = 0
    product_commission_percent: float = 0
    role: RoleSchema | None = None

    @staticmethod
    def resolve_available_shops(obj):
        return obj.get_available_shops()

    @staticmethod
    def resolve_avatar(obj):
        return obj.avatar.url if obj.avatar else None

    @staticmethod
    def resolve_fixed_order_payment(obj):
        return float(obj.fixed_order_payment or 0)

    @staticmethod
    def resolve_service_commission_percent(obj):
        return float(obj.service_commission_percent or 0)

    @staticmethod
    def resolve_product_commission_percent(obj):
        return float(obj.product_commission_percent or 0)


class PermissionSchema(Schema):
    id: int
    name: str
    codename: str
    category: str
    description: str | None = None
