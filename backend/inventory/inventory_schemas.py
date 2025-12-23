from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from ninja import Schema


class SupplierSchema(Schema):
    id: int
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    rating: float
    is_active: bool

    @staticmethod
    def resolve_rating(obj):
        return float(obj.rating or 0)


class InventoryItemSchema(Schema):
    id: int
    name: str
    sku: str
    item_type: str
    category_id: int
    category_name: Optional[str] = None
    primary_supplier_id: Optional[int] = None
    primary_supplier_name: Optional[str] = None
    purchase_price: float
    selling_price: float
    total_stock: int

    @staticmethod
    def resolve_category_name(obj):
        return obj.category.name if obj.category else None

    @staticmethod
    def resolve_primary_supplier_id(obj):
        return obj.primary_supplier_id if obj.primary_supplier_id else None

    @staticmethod
    def resolve_primary_supplier_name(obj):
        return obj.primary_supplier.name if obj.primary_supplier else None

    @staticmethod
    def resolve_purchase_price(obj):
        return float(obj.purchase_price or 0)

    @staticmethod
    def resolve_selling_price(obj):
        return float(obj.selling_price or 0)

    @staticmethod
    def resolve_total_stock(obj):
        # uses @property total_stock on model
        return int(obj.total_stock or 0)


class StockBalanceSchema(Schema):
    id: int
    shop_id: int
    shop_name: str
    item_id: int
    item_name: str
    sku: str
    quantity: int
    reserved_quantity: int
    available_quantity: int
    min_quantity: int
    max_quantity: int
    reorder_point: int
    is_low_stock: bool
    needs_reorder: bool

    @staticmethod
    def resolve_shop_name(obj):
        return obj.shop.name

    @staticmethod
    def resolve_item_name(obj):
        return obj.item.name

    @staticmethod
    def resolve_sku(obj):
        return obj.item.sku

    @staticmethod
    def resolve_is_low_stock(obj):
        return bool(obj.is_low_stock)

    @staticmethod
    def resolve_needs_reorder(obj):
        return bool(obj.needs_reorder)


class StockMovementSchema(Schema):
    id: int
    stock_balance_id: int
    movement_type: str
    quantity_before: int
    quantity_change: int
    quantity_after: int
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    cost_per_unit: Optional[float] = None
    purchase_order_id: Optional[int] = None
    repair_order_id: Optional[int] = None
    created_by_id: int
    created_at: datetime

    @staticmethod
    def resolve_cost_per_unit(obj):
        return float(obj.cost_per_unit) if obj.cost_per_unit is not None else None


class PurchaseOrderItemSchema(Schema):
    id: int
    item_id: int
    item_name: str
    sku: str
    ordered_quantity: int
    received_quantity: int
    unit_price: float
    total_price: float

    @staticmethod
    def resolve_item_name(obj):
        return obj.item.name

    @staticmethod
    def resolve_sku(obj):
        return obj.item.sku

    @staticmethod
    def resolve_unit_price(obj):
        return float(obj.unit_price or 0)

    @staticmethod
    def resolve_total_price(obj):
        return float(obj.total_price or 0)


class PurchaseOrderSchema(Schema):
    id: int
    order_number: str
    status: str

    order_date: datetime
    expected_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None

    subtotal: float
    tax_amount: float
    total_amount: float

    shop_id: int
    shop_name: str

    supplier: SupplierSchema
    items: List[PurchaseOrderItemSchema]

    @staticmethod
    def resolve_subtotal(obj):
        return float(obj.subtotal or 0)

    @staticmethod
    def resolve_tax_amount(obj):
        return float(obj.tax_amount or 0)

    @staticmethod
    def resolve_total_amount(obj):
        return float(obj.total_amount or 0)

    @staticmethod
    def resolve_shop_name(obj):
        return obj.shop.name


class RetailSaleItemSchema(Schema):
    id: int
    item_id: int
    name: str
    sku: str
    barcode: Optional[str] = None
    quantity: int
    unit_price: float
    total_price: float

    @staticmethod
    def resolve_name(obj):
        return obj.item.name

    @staticmethod
    def resolve_sku(obj):
        return obj.item.sku

    @staticmethod
    def resolve_barcode(obj):
        return obj.item.barcode or None

    @staticmethod
    def resolve_unit_price(obj):
        return float(obj.unit_price)

    @staticmethod
    def resolve_total_price(obj):
        return float(obj.total_price)


class RetailSaleSchema(Schema):
    id: int
    sale_number: str
    shop_id: int
    cashier_id: int
    customer_id: Optional[int] = None
    status: str
    subtotal: float
    discount_amount: float
    total_amount: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    items: List[RetailSaleItemSchema]

    @staticmethod
    def resolve_subtotal(obj):
        return float(obj.subtotal or 0)

    @staticmethod
    def resolve_discount_amount(obj):
        return float(obj.discount_amount or 0)

    @staticmethod
    def resolve_total_amount(obj):
        return float(obj.total_amount or 0)
