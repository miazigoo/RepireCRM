from decimal import Decimal
from typing import List, Optional

from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import paginate

from .inventory_schemas import (
    AddBarcodeInputSchema,
    AdHocAdjustmentRequest,
    AdHocOperationResponseSchema,
    AdHocReceiveRequest,
    FinalizeSalePaymentInputSchema,
    FinalizeSaleResponseSchema,
    InventoryItemSchema,
    ItemBarcodeSchema,
    ItemStockByCodeSchema,
    PurchaseOrderSchema,
    QuickCreateItemInputSchema,
    QuickCreateItemResponseSchema,
    RetailSaleItemSchema,
    RetailSaleSchema,
    StockBalanceSchema,
    StockDashboardSchema,
    StockMovementSchema,
    SupplierSchema,
)
from .models import (
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    StockBalance,
    StockMovement,
    Supplier,
)
from .services import InventoryService

router = Router(tags=["Складской учет"])


@router.get("/items", response=List[InventoryItemSchema])
@paginate
def list_inventory_items(request, search: str = None, category_id: int = None):
    """Список товаров"""
    if not request.auth.has_permission("inventory.view_item"):
        raise PermissionError("Нет прав для просмотра товаров")

    queryset = InventoryItem.objects.select_related(
        "category", "primary_supplier"
    ).filter(is_active=True)

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(description__icontains=search)
        )

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    return queryset.order_by("category", "name")


@router.get("/stock-balances", response=List[StockBalanceSchema])
def get_stock_balances(request, shop_id: int = None, low_stock_only: bool = False):
    """Остатки товаров"""
    if not request.auth.has_permission("inventory.view_stock"):
        raise PermissionError("Нет прав для просмотра остатков")

    queryset = StockBalance.objects.select_related("item", "shop").filter(
        item__is_active=True
    )

    # Фильтрация по магазину
    if shop_id:
        queryset = queryset.filter(shop_id=shop_id)
    elif not request.auth.is_director:
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(shop__in=available_shops)

    # Только товары с низким остатком
    if low_stock_only:
        queryset = queryset.filter(quantity__lte=F("min_quantity"))

    return queryset.order_by("item__name")


@router.post("/stock-movement", response=dict)
def create_stock_movement(request, data: dict):
    """Создание движения товара"""
    if not request.auth.has_permission("inventory.add_movement"):
        raise PermissionError("Нет прав для создания движений")

    service = InventoryService()
    movement = service.create_movement(
        stock_balance_id=data["stock_balance_id"],
        movement_type=data["movement_type"],
        quantity_change=data["quantity_change"],
        notes=data.get("notes", ""),
        user=request.auth,
    )

    return {
        "success": True,
        "movement_id": movement.id,
        "new_balance": movement.quantity_after,
    }


@router.get("/purchase-orders", response=List[PurchaseOrderSchema])
@paginate
def list_purchase_orders(request, status: str = None):
    """Заказы поставщикам"""
    if not request.auth.has_permission("inventory.view_purchase_orders"):
        raise PermissionError("Нет прав для просмотра заказов поставщикам")

    queryset = PurchaseOrder.objects.select_related(
        "supplier", "shop", "created_by"
    ).prefetch_related("items__item")

    # Фильтрация по магазину
    if not request.auth.is_director:
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(shop__in=available_shops)

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


@router.post("/purchase-orders", response=dict)
def create_purchase_order(request, data: dict):
    """Создание заказа поставщику"""
    if not request.auth.has_permission("inventory.add_purchase_order"):
        raise PermissionError("Нет прав для создания заказов поставщикам")

    try:
        with transaction.atomic():
            # Создаем заказ
            purchase_order = PurchaseOrder.objects.create(
                supplier_id=data["supplier_id"],
                shop=request.current_shop,
                notes=data.get("notes", ""),
                created_by=request.auth,
            )

            # Добавляем позиции
            total_amount = Decimal("0")
            for item_data in data["items"]:
                po_item = PurchaseOrderItem.objects.create(
                    purchase_order=purchase_order,
                    item_id=item_data["item_id"],
                    ordered_quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                )
                total_amount += po_item.total_price

            # Обновляем общую сумму
            purchase_order.total_amount = total_amount
            purchase_order.save()

            return {
                "success": True,
                "order_id": purchase_order.id,
                "order_number": purchase_order.order_number,
            }

    except Exception as e:
        return {"error": str(e)}


@router.post("/purchase-orders/{order_id}/receive", response=dict)
def receive_purchase_order(request, order_id: int, data: dict):
    """Приемка заказа поставщика"""
    if not request.auth.has_permission("inventory.receive_purchase_orders"):
        raise PermissionError("Нет прав для приемки заказов")

    purchase_order = get_object_or_404(PurchaseOrder, id=order_id)

    service = InventoryService()
    result = service.receive_purchase_order(
        purchase_order=purchase_order, received_items=data["items"], user=request.auth
    )

    return result


@router.get("/suppliers", response=List[SupplierSchema])
def list_suppliers(request, active_only: bool = True):
    """Список поставщиков"""
    if not request.auth.has_permission("inventory.view_suppliers"):
        raise PermissionError("Нет прав для просмотра поставщиков")

    queryset = Supplier.objects.all()

    if active_only:
        queryset = queryset.filter(is_active=True)

    return queryset.order_by("name")


@router.get("/reorder-suggestions", response=List[dict])
def get_reorder_suggestions(request):
    """Рекомендации для перезаказа товаров"""
    if not request.auth.has_permission("inventory.view_stock"):
        raise PermissionError("Нет прав для просмотра остатков")

    service = InventoryService()
    return service.get_reorder_suggestions(request.auth)


@router.post("/barcode/scan", response=dict)
def scan_barcode(request, data: dict):
    """
    Сканирование ШК:
    data = {"barcode": "123456789", "context": "pos" | "inventory", "quantity": 1}
    """
    if not hasattr(request, "current_shop") or not request.current_shop:
        return {"error": "Не выбран текущий магазин"}

    # Проверка флага POS, если контекст POS
    context = data.get("context", "pos")
    if context == "pos":
        settings = getattr(request.current_shop, "settings", None)
        if not (settings and getattr(settings, "pos_barcode_enabled", False)):
            return {"error": "POS с ШК не включен для магазина"}

    service = InventoryService()
    res = service.scan_barcode(
        barcode=data["barcode"],
        shop=request.current_shop,
        user=request.auth,
        context=context,
        quantity=int(data.get("quantity", 1)),
        notes=data.get("notes", ""),
    )
    return res


@router.post("/retail-sales", response=dict)
def create_retail_sale(request, data: dict = None):
    """Создать черновик продажи (POS)"""
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав для создания продаж")
    if not hasattr(request, "current_shop") or not request.current_shop:
        return {"error": "Не выбран текущий магазин"}

    settings = getattr(request.current_shop, "settings", None)
    if not (settings and getattr(settings, "pos_barcode_enabled", False)):
        return {"error": "POS с ШК не включен для магазина"}

    service = InventoryService()
    sale = service.start_sale(
        request.current_shop,
        request.auth,
        customer=None,
        notes=(data or {}).get("notes", ""),
    )
    return {"success": True, "sale_id": sale.id, "sale_number": sale.sale_number}


@router.post("/retail-sales/{sale_id}/items", response=dict)
def add_item_to_retail_sale(request, sale_id: int, data: dict):
    """Добавить товар в продажу по ШК или item_id
    data = {"barcode": "...", "item_id": 1, "quantity": 1}
    """
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав для изменения продаж")

    from .models import RetailSale  # прямой импорт модели

    sale = get_object_or_404(RetailSale, id=sale_id)

    if sale.status != "draft":
        return {"error": "Можно добавлять товары только в черновик продажи"}

    service = InventoryService()
    item = None
    if data.get("item_id"):
        item = get_object_or_404(InventoryItem, id=data["item_id"])
    elif data.get("barcode"):
        item = service.find_item_by_barcode(data["barcode"])
        if not item:
            return {"error": "Товар с таким штрихкодом не найден"}
    else:
        return {"error": "Укажите barcode или item_id"}

    line = service.add_item_to_sale(sale, item, quantity=int(data.get("quantity", 1)))
    return {
        "success": True,
        "line_id": line.id,
        "quantity": line.quantity,
        "unit_price": float(line.unit_price),
        "total_price": float(line.total_price),
    }


@router.post("/retail-sales/{sale_id}/finalize", response=dict)
def finalize_retail_sale(request, sale_id: int):
    """Завершить продажу: спишет остатки и зафиксирует итоги"""
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав для редактирования продаж")

    from .models import RetailSale

    sale = get_object_or_404(RetailSale, id=sale_id)

    service = InventoryService()
    try:
        res = service.finalize_sale(sale, user=request.auth)
        return res
    except ValueError as e:
        return {"error": str(e)}


@router.get("/items/lookup", response=List[InventoryItemSchema])
def lookup_items(request, q: Optional[str] = None, limit: int = 20):
    """
    Поиск товара для селекта: name/sku/barcode.
    """
    if not request.auth.has_permission("inventory.view_item"):
        raise PermissionError("Нет прав для просмотра товаров")

    qs = InventoryItem.objects.filter(is_active=True)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(sku__icontains=q)
            | Q(barcodes__barcode__icontains=q)
        ).distinct()
    return qs.order_by("name")[:limit]


# Дашборд по складу: агрегаты
@router.get("/stock/dashboard", response=StockDashboardSchema)
def stock_dashboard(request):
    if not request.auth.has_permission("inventory.view_stock"):
        raise PermissionError("Нет прав для просмотра остатков")
    service = InventoryService()
    return service.get_stock_dashboard(request.auth)


# Остатки по SKU/ШК
@router.get("/stock/item-by-code", response=ItemStockByCodeSchema)
def stock_item_by_code(
    request, code: Optional[str] = None, barcode: Optional[str] = None
):
    if not request.auth.has_permission("inventory.view_stock"):
        raise PermissionError("Нет прав для просмотра остатков")
    service = InventoryService()
    return service.get_item_stock_by_code(request.auth, code, barcode)


# Быстрое создание товара из модалки
@router.post(
    "/items/quick-create", response={201: QuickCreateItemResponseSchema, 400: dict}
)
def quick_create_item(request, data: QuickCreateItemInputSchema):
    if not request.auth.has_permission("inventory.add_item"):
        raise PermissionError("Нет прав для создания товаров")
    try:
        service = InventoryService()
        item = service.quick_create_item(data.dict(), created_by=request.auth)
        return 201, {
            "id": item.id,
            "name": item.name,
            "sku": item.sku,
            "barcode": item.barcode or None,
            "item_type": item.item_type,
            "category_id": item.category_id,
            "purchase_price": float(item.purchase_price),
            "selling_price": float(item.selling_price),
            "unit": item.unit,
        }
    except ValueError as e:
        return 400, {"error": str(e)}


# Финализация продажи с оплатой
@router.post(
    "/retail-sales/{sale_id}/finalize-with-payment", response=FinalizeSaleResponseSchema
)
def finalize_retail_sale_with_payment(
    request, sale_id: int, payment: FinalizeSalePaymentInputSchema
):
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав для редактирования продаж")
    from .models import RetailSale

    sale = get_object_or_404(RetailSale, id=sale_id)
    service = InventoryService()
    res, _pay = service.finalize_sale_with_payment(
        sale=sale,
        user=request.auth,
        payment_method_id=payment.payment_method_id,
        cash_register_id=payment.cash_register_id,
        description=payment.description or "",
    )
    return {
        "success": res["success"],
        "sale_id": res["sale_id"],
        "sale_number": res["sale_number"],
        "total": res["total"],
        "payment_id": res.get("payment_id"),
        "payment_number": res.get("payment_number"),
    }


@router.post("/receipts/ad-hoc", response=AdHocOperationResponseSchema)
def receive_items_ad_hoc(request, data: AdHocReceiveRequest):
    if not request.auth.has_permission("inventory.add_movement"):
        raise PermissionError("Нет прав для приемки")
    if not hasattr(request, "current_shop") or not request.current_shop:
        return {"success": False, "processed": 0, "ok": 0, "results": [], "error": "Не выбран текущий магазин"}  # type: ignore
    service = InventoryService()
    return service.receive_items_ad_hoc(
        shop=request.current_shop,
        user=request.auth,
        items=[i.dict() for i in data.items],
        common_notes=data.notes or "",
    )


@router.post("/adjustments/ad-hoc", response=AdHocOperationResponseSchema)
def adjust_items_ad_hoc(request, data: AdHocAdjustmentRequest):
    if not request.auth.has_permission("inventory.add_movement"):
        raise PermissionError("Нет прав для корректировок")
    if not hasattr(request, "current_shop") or not request.current_shop:
        return {"success": False, "processed": 0, "ok": 0, "results": [], "error": "Не выбран текущий магазин"}  # type: ignore
    service = InventoryService()
    return service.adjust_items_ad_hoc(
        shop=request.current_shop,
        user=request.auth,
        items=[i.dict() for i in data.items],
        common_notes=data.notes or "",
    )


@router.get("/items/{item_id}/barcodes", response=List[ItemBarcodeSchema])
def list_item_barcodes(request, item_id: int):
    if not request.auth.has_permission("inventory.view_item"):
        raise PermissionError("Нет прав")
    from .models import InventoryItem, InventoryItemBarcode

    item = get_object_or_404(InventoryItem, id=item_id)
    barcodes = InventoryItemBarcode.objects.filter(item=item).order_by("-id")
    return barcodes


@router.post("/items/{item_id}/barcodes", response={201: ItemBarcodeSchema, 400: dict})
def add_item_barcode(request, item_id: int, data: AddBarcodeInputSchema):
    if not request.auth.has_permission("inventory.change_item"):
        raise PermissionError("Нет прав")
    from .models import InventoryItem, InventoryItemBarcode

    item = get_object_or_404(InventoryItem, id=item_id)
    bc = data.barcode.strip()
    if not bc:
        return 400, {"error": "barcode пуст"}
    # проверим уникальность на уровне пары (item, barcode)
    if InventoryItemBarcode.objects.filter(item=item, barcode=bc).exists():
        return 400, {"error": "ШК уже привязан к товару"}

    ib = InventoryItemBarcode.objects.create(
        item=item, barcode=bc, supplier_id=data.supplier_id
    )
    return 201, ib


@router.delete("/items/{item_id}/barcodes/{barcode_id}", response=dict)
def delete_item_barcode(request, item_id: int, barcode_id: int):
    if not request.auth.has_permission("inventory.change_item"):
        raise PermissionError("Нет прав")
    from .models import InventoryItem, InventoryItemBarcode

    item = get_object_or_404(InventoryItem, id=item_id)
    ib = get_object_or_404(InventoryItemBarcode, id=barcode_id, item=item)
    ib.delete()
    return {"success": True}
