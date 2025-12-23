from decimal import Decimal
from typing import List, Optional

from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import paginate

from .inventory_schemas import (
    InventoryItemSchema,
    PurchaseOrderSchema,
    RetailSaleItemSchema,
    RetailSaleSchema,
    StockBalanceSchema,
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

    sale = get_object_or_404(
        PurchaseOrder.__class__.objects.none().__class__.__mro__[1], id=sale_id
    )  # trick to avoid import conflict
    # Правильный импорт:
    from .models import InventoryItem, RetailSale

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
