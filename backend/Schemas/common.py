from ninja import Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class MessageSchema(Schema):
    message: str
    success: bool = True


class ErrorSchema(Schema):
    error: str
    details: Optional[dict] = None


class PaginationSchema(Schema):
    page: int = 1
    page_size: int = 20
    total: int
    total_pages: int


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


class UserSchema(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    is_director: bool
    current_shop: Optional[ShopSchema] = None
    avatar: Optional[str] = None


class RoleSchema(Schema):
    id: int
    name: str
    code: str
    description: Optional[str] = None


class PermissionSchema(Schema):
    id: int
    name: str
    codename: str
    category: str
    description: Optional[str] = None