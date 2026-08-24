from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Body, Router
from ninja.pagination import paginate

from shops.models import Shop

from .inventory_schemas import (
    AddBarcodeInputSchema,
    AdHocAdjustmentRequest,
    AdHocOperationResponseSchema,
    AdHocReceiveRequest,
    FinalizeSalePaymentInputSchema,
    FinalizeSaleResponseSchema,
    InventoryItemSchema,
    InventoryProductGroupSchema,
    ItemBarcodeSchema,
    ItemStockByCodeSchema,
    PurchaseOrderSchema,
    PurchaseRequestBatchCreateSchema,
    PurchaseRequestBatchReceiveSchema,
    PurchaseRequestBatchSchema,
    PurchaseRequestCreateSchema,
    PurchaseRequestItemSchema,
    PurchaseRequestItemUpdateSchema,
    PurchaseRequestSchema,
    PurchaseRequestSplitInputSchema,
    PurchaseRequestStatusInputSchema,
    PurchaseRequestTimelineEventSchema,
    QuickCreateItemInputSchema,
    QuickCreateItemResponseSchema,
    StockBalanceSchema,
    StockDashboardSchema,
    SupplierSchema,
    UpdateInventoryItemInputSchema,
)
from .models import (
    Category,
    InventoryItem,
    InventoryProductGroup,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestAuditLog,
    PurchaseRequestBatch,
    RetailSale,
    StockBalance,
    StockMovement,
    Supplier,
)
from .services import InventoryService

router = Router(tags=["Складской учет"])


def _has_any_permission(user, *codenames: str) -> bool:
    return any(user.has_permission(codename) for codename in codenames)


def _scope_to_current_shop(request, queryset, shop_field: str = "shop"):
    current_shop = getattr(request, "current_shop", None)
    if current_shop:
        return queryset.filter(**{shop_field: current_shop})
    return queryset.filter(**{f"{shop_field}__in": request.auth.get_available_shops()})


def _resolve_stock_shop(request, shop_id: int | None = None):
    current_shop = getattr(request, "current_shop", None)
    if shop_id:
        shop = get_object_or_404(Shop, id=shop_id, is_active=True)
        if request.auth.can_access_shop(shop):
            return shop
        if request.auth.has_permission("inventory.view_other_shop_stock"):
            return shop
        raise PermissionError("Нет прав смотреть остатки выбранного филиала")
    return current_shop


def _get_accessible_sale(request, sale_id: int) -> RetailSale:
    sale = get_object_or_404(RetailSale, id=sale_id)
    current_shop = getattr(request, "current_shop", None)
    if current_shop and sale.shop_id != current_shop.id:
        raise PermissionError("Нет доступа к продаже в другом филиале")
    if not request.auth.can_access_shop(sale.shop):
        raise PermissionError("Нет доступа к продаже в этом филиале")
    return sale


def _purchase_request_queryset():
    return PurchaseRequest.objects.select_related(
        "shop",
        "created_by",
        "reviewed_by",
    ).prefetch_related(
        "items__item__category",
        "items__supplier",
        "items__procurement_group",
        "batches__supplier",
        "batches__procurement_group",
        "batches__purchase_order__items",
        "batches__items__request_item__item",
    )


def _get_accessible_purchase_request(request, request_id: int) -> PurchaseRequest:
    purchase_request = get_object_or_404(_purchase_request_queryset(), id=request_id)
    if not request.auth.can_access_shop(purchase_request.shop):
        raise PermissionError("Нет доступа к заявке другого филиала")
    current_shop = getattr(request, "current_shop", None)
    if current_shop and purchase_request.shop_id != current_shop.id:
        if not request.auth.has_permission("inventory.view_other_shop_stock"):
            raise PermissionError("Нет доступа к заявке другого филиала")
    return purchase_request


def _actor_name(user) -> str | None:
    if not user:
        return None
    return user.get_full_name() or user.username


@router.get("/items", response=list[InventoryItemSchema])
@paginate
def list_inventory_items(
    request, search: str = None, category_id: int = None, shop_id: int = None
):
    """Список товаров"""
    if not request.auth.has_permission("inventory.view_item"):
        raise PermissionError("Нет прав для просмотра товаров")

    # Получаем товары доступные в текущем магазине
    if not hasattr(request, "current_shop") or not request.current_shop:
        raise PermissionError("Магазин не выбран")

    # Товары видны если у них есть остаток в текущем магазине ИЛИ это активные товары
    selected_shop = _resolve_stock_shop(request, shop_id)
    balances = StockBalance.objects.select_related("shop")
    if selected_shop:
        balances = balances.filter(shop=selected_shop)
    else:
        balances = balances.filter(shop__in=request.auth.get_available_shops())

    queryset = (
        InventoryItem.objects.select_related(
            "category", "primary_supplier", "procurement_group"
        )
        .prefetch_related(Prefetch("stock_balances", queryset=balances))
        .filter(is_active=True)
    )

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(description__icontains=search)
        )

    if category_id:
        queryset = queryset.filter(category_id=category_id)

    return queryset.order_by("category", "name")


@router.get("/stock-balances", response=list[StockBalanceSchema])
def get_stock_balances(request, shop_id: int = None, low_stock_only: bool = False):
    """Остатки товаров"""
    if not request.auth.has_permission("inventory.view_stock"):
        raise PermissionError("Нет прав для просмотра остатков")

    queryset = StockBalance.objects.select_related("item", "shop").filter(
        item__is_active=True
    )

    if shop_id:
        shop = _resolve_stock_shop(request, shop_id)
        queryset = queryset.filter(shop=shop)
    else:
        queryset = _scope_to_current_shop(request, queryset)

    # Только товары с низким остатком
    if low_stock_only:
        queryset = queryset.filter(quantity__lte=F("min_quantity"))

    return queryset.order_by("item__name")


@router.post("/stock-movement", response=dict)
def create_stock_movement(request, data: dict = Body(...)):
    """Создание движения товара"""
    if not request.auth.has_permission("inventory.add_movement"):
        raise PermissionError("Нет прав для создания движений")

    balance = get_object_or_404(StockBalance, id=data["stock_balance_id"])
    if not request.auth.can_access_shop(balance.shop):
        raise PermissionError("Нет доступа к остатку данного филиала")
    if request.current_shop and balance.shop_id != request.current_shop.id:
        raise PermissionError("Нет доступа к остатку данного филиала")

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


@router.get("/product-groups", response=list[InventoryProductGroupSchema])
def list_product_groups(request, active_only: bool = True):
    """Группы закупки для номенклатуры."""
    if not request.auth.has_permission("inventory.view_item"):
        raise PermissionError("Нет прав для просмотра групп товаров")

    queryset = InventoryProductGroup.objects.all()
    if active_only:
        queryset = queryset.filter(is_active=True)
    return queryset.order_by("name")


@router.get("/purchase-requests", response=list[PurchaseRequestSchema])
@paginate
def list_purchase_requests(
    request,
    status: str | None = None,
    supplier_id: int | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    search: str | None = None,
):
    """Внутренние заявки склада на закупку."""
    if not _has_any_permission(
        request.auth,
        "inventory.view_purchase_requests",
        "inventory.view_purchase_orders",
        "inventory.view_purchase",
    ):
        raise PermissionError("Нет прав для просмотра заявок на закупку")

    queryset = _scope_to_current_shop(request, _purchase_request_queryset())
    if status:
        queryset = queryset.filter(status=status)
    if supplier_id:
        queryset = queryset.filter(
            Q(items__supplier_id=supplier_id) | Q(batches__supplier_id=supplier_id)
        )
    if due_from:
        queryset = queryset.filter(due_date__gte=due_from)
    if due_to:
        queryset = queryset.filter(due_date__lte=due_to)
    if search:
        normalized = search.strip()
        if normalized:
            queryset = queryset.filter(
                Q(request_number__icontains=normalized)
                | Q(notes__icontains=normalized)
                | Q(items__item__name__icontains=normalized)
                | Q(items__item__sku__icontains=normalized)
            )
    return queryset.distinct().order_by("-created_at")


@router.post("/purchase-requests", response={201: PurchaseRequestSchema, 400: dict})
def create_purchase_request(request, data: PurchaseRequestCreateSchema):
    """Создать заявку на закупку для директора."""
    if not _has_any_permission(
        request.auth,
        "inventory.add_purchase_request",
        "inventory.add_purchase_order",
        "inventory.add_purchase",
    ):
        raise PermissionError("Нет прав для создания заявок на закупку")
    if not getattr(request, "current_shop", None):
        return 400, {"error": "Не выбран магазин для заявки"}

    try:
        service = InventoryService()
        purchase_request = service.create_purchase_request(
            shop=request.current_shop,
            user=request.auth,
            payload=data.model_dump(),
        )
        return 201, _purchase_request_queryset().get(id=purchase_request.id)
    except ValueError as e:
        return 400, {"error": str(e)}


@router.get("/purchase-requests/{request_id}", response=PurchaseRequestSchema)
def get_purchase_request(request, request_id: int):
    if not _has_any_permission(
        request.auth,
        "inventory.view_purchase_requests",
        "inventory.view_purchase_orders",
        "inventory.view_purchase",
    ):
        raise PermissionError("Нет прав для просмотра заявки")
    return _get_accessible_purchase_request(request, request_id)


@router.get(
    "/purchase-requests/{request_id}/timeline",
    response=list[PurchaseRequestTimelineEventSchema],
)
def list_purchase_request_timeline(request, request_id: int):
    if not _has_any_permission(
        request.auth,
        "inventory.view_purchase_requests",
        "inventory.view_purchase_orders",
        "inventory.view_purchase",
    ):
        raise PermissionError("Нет прав для просмотра истории заявки")
    purchase_request = _get_accessible_purchase_request(request, request_id)

    events = []
    for item in purchase_request.status_history.select_related("changed_by").all():
        events.append(
            {
                "id": item.id,
                "event_type": "request_status",
                "action": "status_changed",
                "message": item.comment or "Изменен статус заявки",
                "old_status": item.old_status or None,
                "new_status": item.new_status,
                "batch_id": None,
                "batch_number": None,
                "actor_name": _actor_name(item.changed_by),
                "changes": None,
                "created_at": item.changed_at,
            }
        )

    for batch in purchase_request.batches.all():
        for item in batch.status_history.select_related("changed_by").all():
            events.append(
                {
                    "id": item.id,
                    "event_type": "batch_status",
                    "action": "status_changed",
                    "message": item.comment or "Изменен статус документа",
                    "old_status": item.old_status or None,
                    "new_status": item.new_status,
                    "batch_id": batch.id,
                    "batch_number": batch.batch_number,
                    "actor_name": _actor_name(item.changed_by),
                    "changes": None,
                    "created_at": item.changed_at,
                }
            )

    for item in purchase_request.audit_logs.select_related("actor", "batch").all():
        events.append(
            {
                "id": item.id,
                "event_type": "audit",
                "action": item.action,
                "message": item.message,
                "old_status": None,
                "new_status": None,
                "batch_id": item.batch_id,
                "batch_number": item.batch.batch_number if item.batch else None,
                "actor_name": _actor_name(item.actor),
                "changes": item.changes,
                "created_at": item.created_at,
            }
        )

    return sorted(events, key=lambda event: event["created_at"], reverse=True)


@router.patch(
    "/purchase-requests/{request_id}/items/{request_item_id}",
    response={200: PurchaseRequestItemSchema, 400: dict},
)
def update_purchase_request_item(
    request,
    request_id: int,
    request_item_id: int,
    data: PurchaseRequestItemUpdateSchema,
):
    if not _has_any_permission(
        request.auth,
        "inventory.change_purchase_request",
        "inventory.approve_purchase_request",
        "inventory.add_purchase_order",
    ):
        raise PermissionError("Нет прав для редактирования заявки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    try:
        service = InventoryService()
        item = service.update_purchase_request_item(
            purchase_request,
            request_item_id,
            data.model_dump(exclude_unset=True),
            user=request.auth,
        )
        return 200, item
    except ValueError as e:
        return 400, {"error": str(e)}


@router.post(
    "/purchase-requests/{request_id}/status",
    response={200: PurchaseRequestSchema, 400: dict},
)
def set_purchase_request_status(
    request, request_id: int, data: PurchaseRequestStatusInputSchema
):
    if not _has_any_permission(
        request.auth,
        "inventory.approve_purchase_request",
        "inventory.change_purchase_request",
        "inventory.add_purchase_order",
    ):
        raise PermissionError("Нет прав для согласования заявки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    try:
        service = InventoryService()
        service.set_purchase_request_status(
            purchase_request,
            data.status,
            request.auth,
            reason=data.reason or "",
        )
        return 200, _purchase_request_queryset().get(id=purchase_request.id)
    except ValueError as e:
        return 400, {"error": str(e)}


@router.post(
    "/purchase-requests/{request_id}/split",
    response={200: list[PurchaseRequestBatchSchema], 400: dict},
)
def split_purchase_request(
    request, request_id: int, data: PurchaseRequestSplitInputSchema
):
    if not _has_any_permission(
        request.auth,
        "inventory.approve_purchase_request",
        "inventory.change_purchase_request",
        "inventory.add_purchase_order",
    ):
        raise PermissionError("Нет прав для разбиения заявки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    try:
        service = InventoryService()
        service.split_purchase_request(
            purchase_request,
            user=request.auth,
            mode=data.mode,
            rebuild=data.rebuild,
        )
        refreshed = _purchase_request_queryset().get(id=purchase_request.id)
        return 200, list(refreshed.batches.all())
    except ValueError as e:
        return 400, {"error": str(e)}


@router.post(
    "/purchase-requests/{request_id}/batches",
    response={201: PurchaseRequestBatchSchema, 400: dict},
)
def create_purchase_request_batch(
    request, request_id: int, data: PurchaseRequestBatchCreateSchema
):
    if not _has_any_permission(
        request.auth,
        "inventory.approve_purchase_request",
        "inventory.change_purchase_request",
        "inventory.add_purchase_order",
    ):
        raise PermissionError("Нет прав для разбиения заявки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    try:
        service = InventoryService()
        batch = service.create_purchase_request_batch(
            purchase_request,
            request.auth,
            data.model_dump(),
        )
        return 201, (
            purchase_request.batches.select_related("supplier", "procurement_group")
            .prefetch_related("items__request_item__item")
            .get(id=batch.id)
        )
    except ValueError as e:
        return 400, {"error": str(e)}


@router.get("/purchase-requests/{request_id}/pdf")
def download_purchase_request_pdf(request, request_id: int):
    from .purchase_request_pdf import generate_purchase_request_pdf

    if not _has_any_permission(
        request.auth,
        "inventory.view_purchase_requests",
        "inventory.view_purchase_orders",
        "inventory.view_purchase",
    ):
        raise PermissionError("Нет прав для скачивания заявки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    body = generate_purchase_request_pdf(purchase_request)
    InventoryService().log_purchase_request_event(
        purchase_request,
        PurchaseRequestAuditLog.ActionChoices.PDF_DOWNLOADED,
        f"Скачан PDF заявки {purchase_request.request_number}",
        actor=request.auth,
    )
    filename = f"{purchase_request.request_number}.pdf"
    response = HttpResponse(body, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.get("/purchase-requests/{request_id}/batches/{batch_id}/pdf")
def download_purchase_request_batch_pdf(request, request_id: int, batch_id: int):
    from .purchase_request_pdf import generate_purchase_request_pdf

    if not _has_any_permission(
        request.auth,
        "inventory.view_purchase_requests",
        "inventory.view_purchase_orders",
        "inventory.view_purchase",
    ):
        raise PermissionError("Нет прав для скачивания заявки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    batch = get_object_or_404(purchase_request.batches.all(), id=batch_id)
    body = generate_purchase_request_pdf(purchase_request, batch=batch)
    InventoryService().log_purchase_request_event(
        purchase_request,
        PurchaseRequestAuditLog.ActionChoices.PDF_DOWNLOADED,
        f"Скачан PDF документа {batch.batch_number}",
        actor=request.auth,
        batch=batch,
    )
    filename = f"{batch.batch_number}.pdf"
    response = HttpResponse(body, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.post(
    "/purchase-requests/{request_id}/batches/{batch_id}/purchase-order",
    response={201: dict, 400: dict},
)
def create_purchase_order_from_batch(request, request_id: int, batch_id: int):
    if not _has_any_permission(
        request.auth,
        "inventory.approve_purchase_request",
        "inventory.change_purchase_request",
        "inventory.add_purchase_order",
    ):
        raise PermissionError("Нет прав для создания заказа поставщику")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    batch = get_object_or_404(
        PurchaseRequestBatch.objects.select_related(
            "supplier", "purchase_request__shop", "purchase_order"
        ).prefetch_related("items__request_item__item"),
        id=batch_id,
        purchase_request=purchase_request,
    )
    try:
        service = InventoryService()
        purchase_order = service.create_purchase_order_from_batch(batch, request.auth)
        return 201, {
            "success": True,
            "order_id": purchase_order.id,
            "order_number": purchase_order.order_number,
            "status": purchase_order.status,
        }
    except ValueError as e:
        return 400, {"error": str(e)}


@router.post(
    "/purchase-requests/{request_id}/batches/{batch_id}/receive-full",
    response={200: dict, 400: dict},
)
def receive_purchase_request_batch_full(request, request_id: int, batch_id: int):
    if not _has_any_permission(
        request.auth,
        "inventory.receive_purchase_orders",
        "inventory.receive_purchase",
        "inventory.add_movement",
    ):
        raise PermissionError("Нет прав для приемки поставки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    batch = get_object_or_404(
        PurchaseRequestBatch.objects.select_related(
            "supplier", "purchase_request__shop", "purchase_order"
        ).prefetch_related("items__request_item__item"),
        id=batch_id,
        purchase_request=purchase_request,
    )
    try:
        service = InventoryService()
        return 200, service.receive_purchase_request_batch_full(batch, request.auth)
    except ValueError as e:
        return 400, {"error": str(e)}


@router.post(
    "/purchase-requests/{request_id}/batches/{batch_id}/receive",
    response={200: dict, 400: dict},
)
def receive_purchase_request_batch(
    request, request_id: int, batch_id: int, data: PurchaseRequestBatchReceiveSchema
):
    if not _has_any_permission(
        request.auth,
        "inventory.receive_purchase_orders",
        "inventory.receive_purchase",
        "inventory.add_movement",
    ):
        raise PermissionError("Нет прав для приемки поставки")
    purchase_request = _get_accessible_purchase_request(request, request_id)
    batch = get_object_or_404(
        PurchaseRequestBatch.objects.select_related(
            "supplier", "purchase_request__shop", "purchase_order"
        ).prefetch_related("items__request_item__item"),
        id=batch_id,
        purchase_request=purchase_request,
    )
    try:
        service = InventoryService()
        return 200, service.receive_purchase_request_batch(
            batch,
            data.model_dump()["items"],
            request.auth,
        )
    except ValueError as e:
        return 400, {"error": str(e)}


@router.get("/purchase-orders", response=list[PurchaseOrderSchema])
@paginate
def list_purchase_orders(request, status: str = None):
    """Заказы поставщикам"""
    if not _has_any_permission(
        request.auth, "inventory.view_purchase_orders", "inventory.view_purchase"
    ):
        raise PermissionError("Нет прав для просмотра заказов поставщикам")

    queryset = PurchaseOrder.objects.select_related(
        "supplier", "shop", "created_by"
    ).prefetch_related("items__item")

    # Фильтрация по магазину
    queryset = _scope_to_current_shop(request, queryset)

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


@router.post("/purchase-orders", response={201: dict, 400: dict})
def create_purchase_order(request, data: dict = Body(...)):
    """Создание заказа поставщику"""
    if not _has_any_permission(
        request.auth, "inventory.add_purchase_order", "inventory.add_purchase"
    ):
        raise PermissionError("Нет прав для создания заказов поставщикам")

    try:
        with transaction.atomic():
            shop = getattr(request, "current_shop", None)
            if not shop:
                raise ValueError("Не выбран магазин для заказа поставщику")

            supplier_id = data.get("supplier_id")
            supplier_name = (data.get("supplier_name") or "").strip()
            if supplier_id:
                supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
            elif supplier_name:
                supplier, _ = Supplier.objects.get_or_create(name=supplier_name)
            else:
                raise ValueError("Укажите поставщика")

            items = data.get("items") or []
            if not items:
                raise ValueError("Добавьте хотя бы одну позицию закупки")

            # Создаем заказ
            purchase_order = PurchaseOrder.objects.create(
                supplier=supplier,
                shop=shop,
                notes=data.get("notes", ""),
                created_by=request.auth,
            )

            # Добавляем позиции
            total_amount = Decimal("0")
            for item_data in items:
                quantity = int(item_data["quantity"])
                if quantity <= 0:
                    raise ValueError("Количество должно быть больше нуля")
                po_item = PurchaseOrderItem.objects.create(
                    purchase_order=purchase_order,
                    item_id=item_data["item_id"],
                    ordered_quantity=quantity,
                    unit_price=Decimal(str(item_data["unit_price"])),
                )
                total_amount += po_item.total_price

            # Обновляем общую сумму
            purchase_order.subtotal = total_amount
            purchase_order.total_amount = total_amount
            purchase_order.save(update_fields=["subtotal", "total_amount"])

            return 201, {
                "success": True,
                "order_id": purchase_order.id,
                "order_number": purchase_order.order_number,
            }

    except ValueError as e:
        return 400, {"error": str(e)}


@router.post("/purchase-orders/{order_id}/receive", response=dict)
def receive_purchase_order(request, order_id: int, data: dict = Body(...)):
    """Приемка заказа поставщика"""
    if not _has_any_permission(
        request.auth, "inventory.receive_purchase_orders", "inventory.receive_purchase"
    ):
        raise PermissionError("Нет прав для приемки заказов")

    purchase_order = get_object_or_404(PurchaseOrder, id=order_id)

    if not request.auth.can_access_shop(purchase_order.shop):
        raise PermissionError("Нет доступа к заказу поставщика данного филиала")
    if request.current_shop and purchase_order.shop_id != request.current_shop.id:
        raise PermissionError("Нет доступа к заказу поставщика данного филиала")

    service = InventoryService()
    result = service.receive_purchase_order(
        purchase_order=purchase_order, received_items=data["items"], user=request.auth
    )

    return result


@router.get("/suppliers", response=list[SupplierSchema])
def list_suppliers(request, active_only: bool = True):
    """Список поставщиков"""
    if not _has_any_permission(
        request.auth, "inventory.view_suppliers", "inventory.view_supplier"
    ):
        raise PermissionError("Нет прав для просмотра поставщиков")

    queryset = Supplier.objects.all()

    if active_only:
        queryset = queryset.filter(is_active=True)

    return queryset.order_by("name")


@router.get("/reorder-suggestions", response=list[dict])
def get_reorder_suggestions(request):
    """Рекомендации для перезаказа товаров"""
    if not request.auth.has_permission("inventory.view_stock"):
        raise PermissionError("Нет прав для просмотра остатков")

    service = InventoryService()
    return service.get_reorder_suggestions(
        request.auth, current_shop=getattr(request, "current_shop", None)
    )


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

    sale = _get_accessible_sale(request, sale_id)

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

    sale = _get_accessible_sale(request, sale_id)

    service = InventoryService()
    try:
        res = service.finalize_sale(sale, user=request.auth)
        return res
    except ValueError as e:
        return {"error": str(e)}


@router.get("/items/lookup", response=list[InventoryItemSchema])
def lookup_items(request, q: str | None = None, limit: int = 20):
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
    return service.get_stock_dashboard(
        request.auth, current_shop=getattr(request, "current_shop", None)
    )


# Остатки по SKU/ШК
@router.get("/stock/item-by-code", response=ItemStockByCodeSchema)
def stock_item_by_code(request, code: str | None = None, barcode: str | None = None):
    if not request.auth.has_permission("inventory.view_stock"):
        raise PermissionError("Нет прав для просмотра остатков")
    service = InventoryService()
    return service.get_item_stock_by_code(
        request.auth, code, barcode, current_shop=getattr(request, "current_shop", None)
    )


# Быстрое создание товара из модалки
@router.post(
    "/items/quick-create", response={201: QuickCreateItemResponseSchema, 400: dict}
)
def quick_create_item(request, data: QuickCreateItemInputSchema):
    if not request.auth.has_permission("inventory.add_item"):
        raise PermissionError("Нет прав для создания товаров")
    try:
        service = InventoryService()
        item = service.quick_create_item(data.model_dump(), created_by=request.auth)
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


@router.put("/items/{item_id}", response={200: InventoryItemSchema, 400: dict})
def update_inventory_item(request, item_id: int, data: UpdateInventoryItemInputSchema):
    if not request.auth.has_permission("inventory.change_item"):
        raise PermissionError("Нет прав для редактирования товаров")

    item = get_object_or_404(
        InventoryItem.objects.select_related(
            "category", "primary_supplier", "procurement_group"
        ),
        id=item_id,
        is_active=True,
    )
    payload = data.model_dump(exclude_unset=True)

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return 400, {"error": "Название товара обязательно"}
        item.name = name

    if "sku" in payload:
        sku = (payload.get("sku") or "").strip()
        if not sku:
            return 400, {"error": "Артикул обязателен"}
        if InventoryItem.objects.exclude(id=item.id).filter(sku=sku).exists():
            return 400, {"error": "Товар с таким SKU уже существует"}
        item.sku = sku

    if "item_type" in payload:
        item_type = payload.get("item_type")
        if item_type not in InventoryItem.ItemType.values:
            return 400, {"error": "Некорректный тип товара"}
        item.item_type = item_type

    if payload.get("category_id"):
        item.category = get_object_or_404(Category, id=payload["category_id"])
    elif "category_name" in payload:
        category_name = (payload.get("category_name") or "").strip()
        if not category_name:
            return 400, {"error": "Категория обязательна"}
        category, _ = Category.objects.get_or_create(
            name=category_name,
            defaults={"description": "Категория для складской номенклатуры"},
        )
        item.category = category

    if "procurement_group_id" in payload:
        group_id = payload.get("procurement_group_id")
        item.procurement_group = (
            get_object_or_404(InventoryProductGroup, id=group_id, is_active=True)
            if group_id
            else None
        )
    elif "procurement_group_name" in payload:
        group_name = (payload.get("procurement_group_name") or "").strip()
        item.procurement_group = None
        if group_name:
            item.procurement_group, _ = InventoryProductGroup.objects.get_or_create(
                name=group_name,
                defaults={"description": "Группа закупки складской номенклатуры"},
            )

    if "primary_supplier_id" in payload:
        supplier_id = payload.get("primary_supplier_id")
        item.primary_supplier = (
            get_object_or_404(Supplier, id=supplier_id, is_active=True)
            if supplier_id
            else None
        )

    if "purchase_price" in payload:
        purchase_price = Decimal(str(payload.get("purchase_price") or 0))
        if purchase_price < 0:
            return 400, {"error": "Закупочная цена не может быть отрицательной"}
        item.purchase_price = purchase_price

    if "selling_price" in payload:
        selling_price = Decimal(str(payload.get("selling_price") or 0))
        if selling_price < 0:
            return 400, {"error": "Цена продажи не может быть отрицательной"}
        item.selling_price = selling_price

    if "unit" in payload:
        item.unit = (payload.get("unit") or "шт").strip() or "шт"

    if "description" in payload:
        item.description = (payload.get("description") or "").strip()

    with transaction.atomic():
        item.save()

        if "stock_quantity" in payload or "min_quantity" in payload:
            if not request.auth.has_permission("inventory.add_movement"):
                raise PermissionError("Нет прав для корректировки остатков")
            if not hasattr(request, "current_shop") or not request.current_shop:
                return 400, {"error": "Не выбран текущий магазин"}

            balance, _ = StockBalance.objects.select_for_update().get_or_create(
                shop=request.current_shop,
                item=item,
                defaults={
                    "quantity": 0,
                    "reserved_quantity": 0,
                    "available_quantity": 0,
                },
            )

            if "min_quantity" in payload:
                min_quantity = int(payload.get("min_quantity") or 0)
                if min_quantity < 0:
                    return 400, {
                        "error": "Минимальный остаток не может быть отрицательным"
                    }
                balance.min_quantity = min_quantity
                balance.save(
                    update_fields=[
                        "min_quantity",
                        "available_quantity",
                        "last_movement_date",
                    ]
                )

            if "stock_quantity" in payload:
                stock_quantity = int(payload.get("stock_quantity") or 0)
                if stock_quantity < 0 and not item.allow_negative_stock:
                    return 400, {"error": "Остаток не может быть отрицательным"}
                if stock_quantity < balance.reserved_quantity:
                    return 400, {
                        "error": (
                            "Остаток не может быть меньше "
                            "зарезервированного количества"
                        )
                    }

                quantity_change = stock_quantity - balance.quantity
                if quantity_change:
                    service = InventoryService()
                    service.create_movement(
                        stock_balance_id=balance.id,
                        movement_type=StockMovement.MovementType.ADJUSTMENT,
                        quantity_change=quantity_change,
                        notes="Корректировка из карточки товара",
                        user=request.auth,
                    )

    item = (
        InventoryItem.objects.select_related(
            "category", "primary_supplier", "procurement_group"
        )
        .prefetch_related("stock_balances")
        .get(id=item.id)
    )
    return 200, item


# Финализация продажи с оплатой
@router.post(
    "/retail-sales/{sale_id}/finalize-with-payment", response=FinalizeSaleResponseSchema
)
def finalize_retail_sale_with_payment(
    request, sale_id: int, payment: FinalizeSalePaymentInputSchema
):
    if not request.auth.has_permission("inventory.add_sale"):
        raise PermissionError("Нет прав для редактирования продаж")
    sale = _get_accessible_sale(request, sale_id)
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
        return {  # type: ignore
            "success": False,
            "processed": 0,
            "ok": 0,
            "results": [],
            "error": "Не выбран текущий магазин",
        }
    service = InventoryService()
    return service.receive_items_ad_hoc(
        shop=request.current_shop,
        user=request.auth,
        items=[i.model_dump() for i in data.items],
        common_notes=data.notes or "",
    )


@router.post("/adjustments/ad-hoc", response=AdHocOperationResponseSchema)
def adjust_items_ad_hoc(request, data: AdHocAdjustmentRequest):
    if not request.auth.has_permission("inventory.add_movement"):
        raise PermissionError("Нет прав для корректировок")
    if not hasattr(request, "current_shop") or not request.current_shop:
        return {  # type: ignore
            "success": False,
            "processed": 0,
            "ok": 0,
            "results": [],
            "error": "Не выбран текущий магазин",
        }
    service = InventoryService()
    return service.adjust_items_ad_hoc(
        shop=request.current_shop,
        user=request.auth,
        items=[i.model_dump() for i in data.items],
        common_notes=data.notes or "",
    )


@router.get("/items/{item_id}/barcodes", response=list[ItemBarcodeSchema])
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
