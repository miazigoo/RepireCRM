from datetime import date, datetime
from typing import Any

from ninja import Schema


class SupplierSchema(Schema):
    id: int
    name: str
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    rating: float
    is_active: bool

    @staticmethod
    def resolve_rating(obj):
        return float(obj.rating or 0)


class InventoryProductGroupSchema(Schema):
    id: int
    name: str
    description: str | None = None
    is_active: bool


class InventoryItemSchema(Schema):
    id: int
    name: str
    sku: str
    item_type: str
    category_id: int
    category_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    primary_supplier_id: int | None = None
    primary_supplier_name: str | None = None
    purchase_price: float
    selling_price: float
    total_stock: int
    min_quantity: int
    stock_status: str
    last_movement_date: datetime | None = None

    @staticmethod
    def _stock_balances(obj):
        return list(obj.stock_balances.all())

    @staticmethod
    def resolve_category_name(obj):
        return obj.category.name if obj.category else None

    @staticmethod
    def resolve_procurement_group_id(obj):
        return obj.procurement_group_id if obj.procurement_group_id else None

    @staticmethod
    def resolve_procurement_group_name(obj):
        return obj.procurement_group.name if obj.procurement_group else None

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

    @staticmethod
    def resolve_min_quantity(obj):
        balances = InventoryItemSchema._stock_balances(obj)
        if not balances:
            return 0
        return min(balance.min_quantity for balance in balances)

    @staticmethod
    def resolve_stock_status(obj):
        balances = InventoryItemSchema._stock_balances(obj)
        if not balances:
            return "out_of_stock"

        available_quantity = sum(balance.available_quantity for balance in balances)
        if available_quantity <= 0:
            return "out_of_stock"

        if any(
            balance.available_quantity <= balance.min_quantity for balance in balances
        ):
            return "low_stock"

        return "in_stock"

    @staticmethod
    def resolve_last_movement_date(obj):
        balances = InventoryItemSchema._stock_balances(obj)
        if not balances:
            return None
        return max(balance.last_movement_date for balance in balances)


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
    reference_number: str | None = None
    notes: str | None = None
    cost_per_unit: float | None = None
    purchase_order_id: int | None = None
    repair_order_id: int | None = None
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
    expected_delivery_date: datetime | None = None
    actual_delivery_date: datetime | None = None

    subtotal: float
    tax_amount: float
    total_amount: float

    shop_id: int
    shop_name: str

    supplier: SupplierSchema
    items: list[PurchaseOrderItemSchema]

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


class PurchaseRequestItemSchema(Schema):
    id: int
    item_id: int
    item_name: str
    sku: str
    category_name: str | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    requested_quantity: int
    approved_quantity: int
    received_quantity: int
    unit_price: float
    total_price: float
    notes: str | None = None

    @staticmethod
    def resolve_item_name(obj):
        return obj.item.name

    @staticmethod
    def resolve_sku(obj):
        return obj.item.sku

    @staticmethod
    def resolve_category_name(obj):
        return obj.item.category.name if obj.item.category else None

    @staticmethod
    def resolve_supplier_id(obj):
        return obj.supplier_id if obj.supplier_id else None

    @staticmethod
    def resolve_supplier_name(obj):
        return obj.supplier.name if obj.supplier else None

    @staticmethod
    def resolve_procurement_group_id(obj):
        return obj.procurement_group_id if obj.procurement_group_id else None

    @staticmethod
    def resolve_procurement_group_name(obj):
        return obj.procurement_group.name if obj.procurement_group else None

    @staticmethod
    def resolve_unit_price(obj):
        return float(obj.unit_price or 0)

    @staticmethod
    def resolve_total_price(obj):
        return float(obj.total_price or 0)


class PurchaseRequestBatchItemSchema(Schema):
    id: int
    request_item_id: int
    item_id: int
    item_name: str
    sku: str
    quantity: int
    received_quantity: int
    remaining_quantity: int
    unit_price: float
    total_price: float
    notes: str | None = None

    @staticmethod
    def resolve_request_item_id(obj):
        return obj.request_item_id

    @staticmethod
    def resolve_item_id(obj):
        return obj.request_item.item_id

    @staticmethod
    def resolve_item_name(obj):
        return obj.request_item.item.name

    @staticmethod
    def resolve_sku(obj):
        return obj.request_item.item.sku

    @staticmethod
    def resolve_received_quantity(obj):
        purchase_order = getattr(obj.batch, "purchase_order", None)
        if not purchase_order:
            return 0
        for order_item in purchase_order.items.all():
            if order_item.item_id == obj.request_item.item_id:
                return min(order_item.received_quantity or 0, obj.quantity)
        return 0

    @staticmethod
    def resolve_remaining_quantity(obj):
        received = PurchaseRequestBatchItemSchema.resolve_received_quantity(obj)
        return max((obj.quantity or 0) - received, 0)

    @staticmethod
    def resolve_unit_price(obj):
        return float(obj.unit_price or 0)

    @staticmethod
    def resolve_total_price(obj):
        return float(obj.total_price or 0)


class PurchaseRequestBatchSchema(Schema):
    id: int
    batch_number: str
    title: str
    status: str
    purchase_order_id: int | None = None
    purchase_order_number: str | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    subtotal: float
    total_amount: float
    notes: str | None = None
    created_at: datetime
    items: list[PurchaseRequestBatchItemSchema]

    @staticmethod
    def resolve_purchase_order_id(obj):
        return obj.purchase_order_id if obj.purchase_order_id else None

    @staticmethod
    def resolve_purchase_order_number(obj):
        return obj.purchase_order.order_number if obj.purchase_order else None

    @staticmethod
    def resolve_supplier_id(obj):
        return obj.supplier_id if obj.supplier_id else None

    @staticmethod
    def resolve_supplier_name(obj):
        return obj.supplier.name if obj.supplier else None

    @staticmethod
    def resolve_procurement_group_id(obj):
        return obj.procurement_group_id if obj.procurement_group_id else None

    @staticmethod
    def resolve_procurement_group_name(obj):
        return obj.procurement_group.name if obj.procurement_group else None

    @staticmethod
    def resolve_subtotal(obj):
        return float(obj.subtotal or 0)

    @staticmethod
    def resolve_total_amount(obj):
        return float(obj.total_amount or 0)


class PurchaseRequestSchema(Schema):
    id: int
    request_number: str
    status: str
    priority: str
    due_date: date | None = None
    subtotal: float
    total_amount: float
    notes: str | None = None
    rejection_reason: str | None = None
    shop_id: int
    shop_name: str
    created_by_id: int
    created_by_name: str
    reviewed_by_id: int | None = None
    reviewed_by_name: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items_count: int
    batches_count: int
    items: list[PurchaseRequestItemSchema]
    batches: list[PurchaseRequestBatchSchema]

    @staticmethod
    def resolve_subtotal(obj):
        return float(obj.subtotal or 0)

    @staticmethod
    def resolve_total_amount(obj):
        return float(obj.total_amount or 0)

    @staticmethod
    def resolve_shop_name(obj):
        return obj.shop.name

    @staticmethod
    def resolve_created_by_name(obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    @staticmethod
    def resolve_reviewed_by_id(obj):
        return obj.reviewed_by_id if obj.reviewed_by_id else None

    @staticmethod
    def resolve_reviewed_by_name(obj):
        if not obj.reviewed_by:
            return None
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.username

    @staticmethod
    def resolve_items_count(obj):
        return obj.items_count

    @staticmethod
    def resolve_batches_count(obj):
        return obj.batches_count


class PurchaseRequestItemInputSchema(Schema):
    item_id: int
    quantity: int
    unit_price: float | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    notes: str | None = None


class PurchaseRequestCreateSchema(Schema):
    priority: str | None = "normal"
    due_date: date | None = None
    notes: str | None = None
    as_draft: bool | None = False
    items: list[PurchaseRequestItemInputSchema]


class PurchaseRequestItemUpdateSchema(Schema):
    requested_quantity: int | None = None
    approved_quantity: int | None = None
    unit_price: float | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    notes: str | None = None


class PurchaseRequestStatusInputSchema(Schema):
    status: str
    reason: str | None = None


class PurchaseRequestSplitInputSchema(Schema):
    mode: str = "supplier"
    rebuild: bool = True


class PurchaseRequestBatchItemInputSchema(Schema):
    request_item_id: int
    quantity: int
    unit_price: float | None = None
    notes: str | None = None


class PurchaseRequestBatchCreateSchema(Schema):
    supplier_id: int | None = None
    supplier_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    title: str | None = None
    notes: str | None = None
    items: list[PurchaseRequestBatchItemInputSchema]


class PurchaseRequestBatchReceiveItemInputSchema(Schema):
    batch_item_id: int
    received_quantity: int


class PurchaseRequestBatchReceiveSchema(Schema):
    items: list[PurchaseRequestBatchReceiveItemInputSchema]


class PurchaseRequestTimelineEventSchema(Schema):
    id: int
    event_type: str
    action: str | None = None
    message: str
    old_status: str | None = None
    new_status: str | None = None
    batch_id: int | None = None
    batch_number: str | None = None
    actor_name: str | None = None
    changes: dict[str, Any] | None = None
    created_at: datetime


class RetailSaleItemSchema(Schema):
    id: int
    item_id: int
    name: str
    sku: str
    barcode: str | None = None
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
        # берем первый привязанный ШК (если нужен)
        bc = getattr(obj.item, "barcodes", None)
        if bc:
            first = bc.first()
            return first.barcode if first else None
        return None

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
    customer_id: int | None = None
    status: str
    subtotal: float
    discount_amount: float
    total_amount: float
    created_at: datetime
    completed_at: datetime | None = None
    items: list[RetailSaleItemSchema]

    @staticmethod
    def resolve_subtotal(obj):
        return float(obj.subtotal or 0)

    @staticmethod
    def resolve_discount_amount(obj):
        return float(obj.discount_amount or 0)

    @staticmethod
    def resolve_total_amount(obj):
        return float(obj.total_amount or 0)


# Ad-hoc приемка/корректировка: вход
class AdHocReceiveItemInput(Schema):
    item_id: int | None = None
    barcode: str | None = None
    quantity: int
    cost_per_unit: float | None = None
    notes: str | None = None


class AdHocAdjustmentItemInput(Schema):
    item_id: int | None = None
    barcode: str | None = None
    quantity_change: int
    notes: str | None = None


class AdHocReceiveRequest(Schema):
    items: list[AdHocReceiveItemInput]
    notes: str | None = None


class AdHocAdjustmentRequest(Schema):
    items: list[AdHocAdjustmentItemInput]
    notes: str | None = None


# Ad-hoc: результат по позиции и общий ответ
class AdHocOperationItemResultSchema(Schema):
    ok: bool
    item_id: int | None = None
    name: str | None = None
    quantity_added: int | None = None
    quantity_change: int | None = None
    new_quantity: int | None = None
    error: str | None = None
    entry: dict[str, Any] | None = None


class AdHocOperationResponseSchema(Schema):
    success: bool
    processed: int
    ok: int
    results: list[AdHocOperationItemResultSchema]


# Агрегации/дашборд по складу
class StockByShopItemSchema(Schema):
    shop_id: int
    shop_name: str
    total_quantity: int
    low_stock_count: int


class StockByCategoryItemSchema(Schema):
    category_id: int
    category_name: str
    total_quantity: int
    low_stock_count: int


class StockTotalsSchema(Schema):
    total_skus: int
    total_quantity: int
    low_stock_count: int


class StockDashboardSchema(Schema):
    totals: StockTotalsSchema
    by_shop: list[StockByShopItemSchema]
    by_category: list[StockByCategoryItemSchema]


# Остатки по SKU/ШК
class ItemStockBalanceSchema(Schema):
    shop_id: int
    shop_name: str
    quantity: int
    reserved_quantity: int
    available_quantity: int


class ItemStockByCodeSchema(Schema):
    found: bool
    error: str | None = None
    item_id: int | None = None
    name: str | None = None
    sku: str | None = None
    barcode: str | None = None
    balances: list[ItemStockBalanceSchema] | None = None


# Быстрое создание товара («модалка»)
class QuickCreateItemInputSchema(Schema):
    name: str
    sku: str
    item_type: str
    category_id: int | None = None
    category_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    purchase_price: float
    selling_price: float
    # список штрихкодов
    barcodes: list[str] | None = None
    unit: str | None = "шт"
    primary_supplier_id: int | None = None
    description: str | None = None


class UpdateInventoryItemInputSchema(Schema):
    name: str | None = None
    sku: str | None = None
    item_type: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    procurement_group_id: int | None = None
    procurement_group_name: str | None = None
    primary_supplier_id: int | None = None
    purchase_price: float | None = None
    selling_price: float | None = None
    stock_quantity: int | None = None
    min_quantity: int | None = None
    unit: str | None = None
    description: str | None = None


class QuickCreateItemResponseSchema(Schema):
    id: int
    name: str
    sku: str
    barcode: str | None = None
    item_type: str
    category_id: int
    purchase_price: float
    selling_price: float
    unit: str


# Оплата розничной продажи
class FinalizeSalePaymentInputSchema(Schema):
    payment_method_id: int
    cash_register_id: int | None = None
    description: str | None = None


class FinalizeSaleResponseSchema(Schema):
    success: bool
    sale_id: int
    sale_number: str
    total: float
    payment_id: int | None = None
    payment_number: str | None = None


class ItemBarcodeSchema(Schema):
    id: int
    barcode: str
    supplier_id: int | None = None


class AddBarcodeInputSchema(Schema):
    barcode: str
    supplier_id: int | None = None
