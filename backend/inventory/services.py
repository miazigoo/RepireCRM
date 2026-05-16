from datetime import datetime, time
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from finance.models import CashRegister, Payment, PaymentMethod
from users.models import User

from .models import (
    BarcodeScanEvent,
    Category,
    InventoryItem,
    InventoryItemBarcode,
    InventoryItemCostHistory,
    InventoryProductGroup,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestAuditLog,
    PurchaseRequestBatch,
    PurchaseRequestBatchItem,
    PurchaseRequestBatchStatusHistory,
    PurchaseRequestItem,
    PurchaseRequestStatusHistory,
    RetailSale,
    RetailSaleItem,
    StockBalance,
    StockMovement,
    Supplier,
    SupplierItem,
)


class InventoryService:
    """Складские операции"""

    def _resolve_supplier_from_payload(self, payload: dict) -> Supplier | None:
        supplier_id = payload.get("supplier_id")
        supplier_name = (payload.get("supplier_name") or "").strip()
        if supplier_id:
            return get_object_or_404(Supplier, id=supplier_id, is_active=True)
        if supplier_name:
            supplier, _ = Supplier.objects.get_or_create(name=supplier_name)
            return supplier
        return None

    def _resolve_procurement_group_from_payload(
        self, payload: dict
    ) -> InventoryProductGroup | None:
        group_id = payload.get("procurement_group_id")
        group_name = (payload.get("procurement_group_name") or "").strip()
        if group_id:
            return get_object_or_404(InventoryProductGroup, id=group_id, is_active=True)
        if group_name:
            group, _ = InventoryProductGroup.objects.get_or_create(name=group_name)
            return group
        return None

    def log_purchase_request_event(
        self,
        purchase_request: PurchaseRequest,
        action: str,
        message: str,
        actor: User | None = None,
        batch: PurchaseRequestBatch | None = None,
        changes: dict | None = None,
    ) -> None:
        PurchaseRequestAuditLog.objects.create(
            purchase_request=purchase_request,
            batch=batch,
            action=action,
            actor=actor,
            message=message[:255],
            changes=changes or {},
        )

    def _record_purchase_request_status(
        self,
        purchase_request: PurchaseRequest,
        old_status: str,
        new_status: str,
        user: User | None = None,
        comment: str = "",
    ) -> None:
        if old_status == new_status:
            return
        PurchaseRequestStatusHistory.objects.create(
            purchase_request=purchase_request,
            old_status=old_status or "",
            new_status=new_status,
            changed_by=user,
            comment=comment,
        )

    def _record_purchase_request_batch_status(
        self,
        batch: PurchaseRequestBatch,
        old_status: str,
        new_status: str,
        user: User | None = None,
        comment: str = "",
    ) -> None:
        if old_status == new_status:
            return
        PurchaseRequestBatchStatusHistory.objects.create(
            batch=batch,
            old_status=old_status or "",
            new_status=new_status,
            changed_by=user,
            comment=comment,
        )

    @transaction.atomic
    def create_purchase_request(
        self, shop, user: User, payload: dict
    ) -> PurchaseRequest:
        items = payload.get("items") or []
        if not items:
            raise ValueError("Добавьте хотя бы одну позицию заявки")

        priority = payload.get("priority") or PurchaseRequest.Priority.NORMAL
        if priority not in PurchaseRequest.Priority.values:
            raise ValueError("Некорректный приоритет заявки")

        request = PurchaseRequest.objects.create(
            shop=shop,
            created_by=user,
            status=PurchaseRequest.Status.DRAFT
            if payload.get("as_draft")
            else PurchaseRequest.Status.SUBMITTED,
            priority=priority,
            due_date=payload.get("due_date"),
            notes=(payload.get("notes") or "").strip(),
        )

        seen_item_ids: set[int] = set()
        for row in items:
            item = get_object_or_404(
                InventoryItem.objects.select_related(
                    "primary_supplier", "procurement_group", "category"
                ),
                id=row.get("item_id"),
                is_active=True,
            )
            if item.id in seen_item_ids:
                raise ValueError(f"Товар {item.name} уже добавлен в заявку")
            seen_item_ids.add(item.id)

            quantity = int(row.get("quantity") or 0)
            if quantity <= 0:
                raise ValueError("Количество в заявке должно быть больше нуля")

            supplier = self._resolve_supplier_from_payload(row) or item.primary_supplier
            group = (
                self._resolve_procurement_group_from_payload(row)
                or item.procurement_group
            )
            unit_price = Decimal(
                str(
                    row.get("unit_price")
                    if row.get("unit_price") is not None
                    else item.purchase_price
                )
            )
            if unit_price < 0:
                raise ValueError("Ожидаемая цена не может быть отрицательной")

            PurchaseRequestItem.objects.create(
                purchase_request=request,
                item=item,
                supplier=supplier,
                procurement_group=group,
                requested_quantity=quantity,
                approved_quantity=quantity,
                unit_price=unit_price,
                notes=(row.get("notes") or "").strip(),
            )

        request.recalculate_totals()
        self._record_purchase_request_status(
            request,
            "",
            request.status,
            user,
            "Заявка создана",
        )
        self.log_purchase_request_event(
            request,
            PurchaseRequestAuditLog.ActionChoices.CREATED,
            f"Создана заявка {request.request_number}",
            actor=user,
            changes={
                "items_count": len(items),
                "priority": request.priority,
                "total_amount": str(request.total_amount),
            },
        )
        return request

    @transaction.atomic
    def update_purchase_request_item(
        self,
        purchase_request: PurchaseRequest,
        request_item_id: int,
        payload: dict,
        user: User | None = None,
    ) -> PurchaseRequestItem:
        request_item = get_object_or_404(
            PurchaseRequestItem.objects.select_for_update().select_related("item"),
            id=request_item_id,
            purchase_request=purchase_request,
        )
        if purchase_request.status in {
            PurchaseRequest.Status.SENT,
            PurchaseRequest.Status.PARTIALLY_RECEIVED,
            PurchaseRequest.Status.RECEIVED,
            PurchaseRequest.Status.REJECTED,
            PurchaseRequest.Status.CANCELLED,
        }:
            raise ValueError(
                "Заявку нельзя менять после отправки, отклонения или закрытия"
            )
        if purchase_request.batches.filter(purchase_order__isnull=False).exists():
            raise ValueError("Заявку нельзя менять после создания заказа поставщику")

        old_request_status = purchase_request.status
        had_batches = purchase_request.batches.exists()
        before = {
            "requested_quantity": request_item.requested_quantity,
            "approved_quantity": request_item.approved_quantity,
            "unit_price": str(request_item.unit_price),
            "supplier_id": request_item.supplier_id,
            "procurement_group_id": request_item.procurement_group_id,
            "notes": request_item.notes,
        }

        if (
            "requested_quantity" in payload
            and payload["requested_quantity"] is not None
        ):
            quantity = int(payload["requested_quantity"])
            if quantity <= 0:
                raise ValueError("Запрошенное количество должно быть больше нуля")
            request_item.requested_quantity = quantity
            if not payload.get("approved_quantity"):
                request_item.approved_quantity = quantity

        if "approved_quantity" in payload and payload["approved_quantity"] is not None:
            approved_quantity = int(payload["approved_quantity"])
            if approved_quantity <= 0:
                raise ValueError("Согласованное количество должно быть больше нуля")
            if approved_quantity < request_item.received_quantity:
                raise ValueError("Согласовано меньше уже полученного количества")
            request_item.approved_quantity = approved_quantity

        if "unit_price" in payload and payload["unit_price"] is not None:
            unit_price = Decimal(str(payload["unit_price"]))
            if unit_price < 0:
                raise ValueError("Ожидаемая цена не может быть отрицательной")
            request_item.unit_price = unit_price

        if "supplier_id" in payload or "supplier_name" in payload:
            request_item.supplier = self._resolve_supplier_from_payload(payload)

        if "procurement_group_id" in payload or "procurement_group_name" in payload:
            request_item.procurement_group = (
                self._resolve_procurement_group_from_payload(payload)
            )

        if "notes" in payload:
            request_item.notes = (payload.get("notes") or "").strip()

        request_item.save()
        after = {
            "requested_quantity": request_item.requested_quantity,
            "approved_quantity": request_item.approved_quantity,
            "unit_price": str(request_item.unit_price),
            "supplier_id": request_item.supplier_id,
            "procurement_group_id": request_item.procurement_group_id,
            "notes": request_item.notes,
        }
        changes = {
            key: {"old": before[key], "new": after[key]}
            for key in before
            if before[key] != after[key]
        }
        purchase_request.batches.all().delete()
        if purchase_request.status == PurchaseRequest.Status.SPLIT:
            purchase_request.status = PurchaseRequest.Status.APPROVED
            purchase_request.save(update_fields=["status", "updated_at"])
            self._record_purchase_request_status(
                purchase_request,
                old_request_status,
                purchase_request.status,
                user,
                "Позиция изменена, документы разбиения сброшены",
            )
        purchase_request.recalculate_totals()
        if changes or had_batches:
            self.log_purchase_request_event(
                purchase_request,
                PurchaseRequestAuditLog.ActionChoices.UPDATED,
                f"Обновлена позиция {request_item.item.name}",
                actor=user,
                changes={
                    "item_id": request_item.item_id,
                    "fields": changes,
                    "batches_reset": had_batches,
                },
            )
        return request_item

    @transaction.atomic
    def set_purchase_request_status(
        self,
        purchase_request: PurchaseRequest,
        status: str,
        user: User,
        reason: str = "",
    ) -> PurchaseRequest:
        if status not in PurchaseRequest.Status.values:
            raise ValueError("Некорректный статус заявки")

        old_status = purchase_request.status
        if old_status == status and not reason:
            return purchase_request

        endpoint_statuses = {
            PurchaseRequest.Status.APPROVED,
            PurchaseRequest.Status.REJECTED,
            PurchaseRequest.Status.CANCELLED,
        }
        if status not in endpoint_statuses:
            raise ValueError("Этот статус выставляется отдельным действием")

        terminal_statuses = {
            PurchaseRequest.Status.SENT,
            PurchaseRequest.Status.PARTIALLY_RECEIVED,
            PurchaseRequest.Status.RECEIVED,
            PurchaseRequest.Status.REJECTED,
            PurchaseRequest.Status.CANCELLED,
        }
        if old_status in terminal_statuses:
            raise ValueError("Текущий статус заявки нельзя изменить вручную")

        purchase_request.status = status
        if status == PurchaseRequest.Status.APPROVED:
            purchase_request.reviewed_by = user
            purchase_request.approved_at = timezone.now()
        if status == PurchaseRequest.Status.REJECTED:
            purchase_request.reviewed_by = user
            purchase_request.rejection_reason = reason.strip()
        purchase_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "approved_at",
                "rejection_reason",
                "updated_at",
            ]
        )
        self._record_purchase_request_status(
            purchase_request,
            old_status,
            status,
            user,
            reason.strip(),
        )
        if old_status != status or reason:
            self.log_purchase_request_event(
                purchase_request,
                PurchaseRequestAuditLog.ActionChoices.STATUS_CHANGED,
                f"Статус заявки изменен: {old_status or 'new'} -> {status}",
                actor=user,
                changes={
                    "old_status": old_status,
                    "new_status": status,
                    "reason": reason.strip(),
                },
            )
        return purchase_request

    @transaction.atomic
    def split_purchase_request(
        self,
        purchase_request: PurchaseRequest,
        user: User,
        mode: str = "supplier",
        rebuild: bool = True,
    ) -> list[PurchaseRequestBatch]:
        if mode not in {"supplier", "group", "supplier_group"}:
            raise ValueError("Некорректный режим разбиения")
        if purchase_request.status in {
            PurchaseRequest.Status.SENT,
            PurchaseRequest.Status.PARTIALLY_RECEIVED,
            PurchaseRequest.Status.RECEIVED,
            PurchaseRequest.Status.CANCELLED,
            PurchaseRequest.Status.REJECTED,
        }:
            raise ValueError("Эту заявку нельзя разбить")

        existing_batches = purchase_request.batches.all()
        if rebuild and existing_batches.filter(purchase_order__isnull=False).exists():
            raise ValueError(
                "Нельзя пересобрать документы после создания заказа поставщику"
            )

        if rebuild:
            purchase_request.batches.all().delete()

        batches_by_key: dict[tuple[int | None, int | None], PurchaseRequestBatch] = {}
        old_request_status = purchase_request.status
        request_items = purchase_request.items.select_related(
            "item", "supplier", "procurement_group"
        ).order_by("id")

        for request_item in request_items:
            supplier = request_item.supplier
            group = request_item.procurement_group
            if mode == "supplier":
                key = (supplier.id if supplier else None, None)
                group_for_batch = None
            elif mode == "group":
                key = (None, group.id if group else None)
                supplier_for_batch = None
                group_for_batch = group
            else:
                key = (
                    supplier.id if supplier else None,
                    group.id if group else None,
                )
                supplier_for_batch = supplier
                group_for_batch = group

            if mode == "supplier":
                supplier_for_batch = supplier

            batch = batches_by_key.get(key)
            if batch is None:
                batch = PurchaseRequestBatch.objects.create(
                    purchase_request=purchase_request,
                    supplier=supplier_for_batch,
                    procurement_group=group_for_batch,
                    created_by=user,
                )
                self._record_purchase_request_batch_status(
                    batch,
                    "",
                    batch.status,
                    user,
                    "Документ создан при автоматическом разбиении",
                )
                self.log_purchase_request_event(
                    purchase_request,
                    PurchaseRequestAuditLog.ActionChoices.BATCH_CREATED,
                    f"Создан документ {batch.batch_number}",
                    actor=user,
                    batch=batch,
                    changes={
                        "mode": mode,
                        "supplier_id": batch.supplier_id,
                        "procurement_group_id": batch.procurement_group_id,
                    },
                )
                batches_by_key[key] = batch

            quantity = request_item.approved_quantity or request_item.requested_quantity
            if quantity <= 0:
                continue
            PurchaseRequestBatchItem.objects.create(
                batch=batch,
                request_item=request_item,
                quantity=quantity,
                unit_price=request_item.unit_price,
                notes=request_item.notes,
            )
            batch.recalculate_totals()

        if batches_by_key and purchase_request.status in {
            PurchaseRequest.Status.DRAFT,
            PurchaseRequest.Status.SUBMITTED,
            PurchaseRequest.Status.APPROVED,
        }:
            purchase_request.status = PurchaseRequest.Status.SPLIT
            purchase_request.reviewed_by = user
            if not purchase_request.approved_at:
                purchase_request.approved_at = timezone.now()
            purchase_request.save(
                update_fields=["status", "reviewed_by", "approved_at", "updated_at"]
            )
            self._record_purchase_request_status(
                purchase_request,
                old_request_status,
                purchase_request.status,
                user,
                "Заявка разбита на документы поставщикам",
            )

        if batches_by_key:
            self.log_purchase_request_event(
                purchase_request,
                PurchaseRequestAuditLog.ActionChoices.SPLIT,
                f"Заявка разбита на {len(batches_by_key)} документ(ов)",
                actor=user,
                changes={"mode": mode, "rebuild": rebuild},
            )

        return list(batches_by_key.values())

    @transaction.atomic
    def create_purchase_request_batch(
        self, purchase_request: PurchaseRequest, user: User, payload: dict
    ) -> PurchaseRequestBatch:
        if purchase_request.status in {
            PurchaseRequest.Status.SENT,
            PurchaseRequest.Status.PARTIALLY_RECEIVED,
            PurchaseRequest.Status.RECEIVED,
            PurchaseRequest.Status.CANCELLED,
            PurchaseRequest.Status.REJECTED,
        }:
            raise ValueError("Эту заявку нельзя разбить")
        if not payload.get("items"):
            raise ValueError("Добавьте позиции в документ поставщику")

        old_request_status = purchase_request.status
        supplier = self._resolve_supplier_from_payload(payload)
        group = self._resolve_procurement_group_from_payload(payload)
        batch = PurchaseRequestBatch.objects.create(
            purchase_request=purchase_request,
            supplier=supplier,
            procurement_group=group,
            title=(payload.get("title") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        self._record_purchase_request_batch_status(
            batch,
            "",
            batch.status,
            user,
            "Документ создан вручную",
        )

        for row in payload["items"]:
            request_item = get_object_or_404(
                PurchaseRequestItem,
                id=row.get("request_item_id"),
                purchase_request=purchase_request,
            )
            quantity = int(row.get("quantity") or 0)
            if quantity <= 0:
                raise ValueError("Количество в документе должно быть больше нуля")
            approved = request_item.approved_quantity or request_item.requested_quantity
            already_batched = (
                request_item.batch_items.aggregate(total=Sum("quantity"))["total"] or 0
            )
            if quantity > approved - already_batched:
                raise ValueError("Количество превышает нераспределенный остаток")
            unit_price = Decimal(str(row.get("unit_price") or request_item.unit_price))
            if unit_price < 0:
                raise ValueError("Цена не может быть отрицательной")
            PurchaseRequestBatchItem.objects.create(
                batch=batch,
                request_item=request_item,
                quantity=quantity,
                unit_price=unit_price,
                notes=(row.get("notes") or "").strip(),
            )

        batch.recalculate_totals()
        if purchase_request.status in {
            PurchaseRequest.Status.DRAFT,
            PurchaseRequest.Status.SUBMITTED,
            PurchaseRequest.Status.APPROVED,
        }:
            purchase_request.status = PurchaseRequest.Status.SPLIT
            purchase_request.reviewed_by = user
            if not purchase_request.approved_at:
                purchase_request.approved_at = timezone.now()
            purchase_request.save(
                update_fields=["status", "reviewed_by", "approved_at", "updated_at"]
            )
            self._record_purchase_request_status(
                purchase_request,
                old_request_status,
                purchase_request.status,
                user,
                "Создан ручной документ поставщику",
            )
        self.log_purchase_request_event(
            purchase_request,
            PurchaseRequestAuditLog.ActionChoices.BATCH_CREATED,
            f"Создан документ {batch.batch_number}",
            actor=user,
            batch=batch,
            changes={
                "supplier_id": batch.supplier_id,
                "procurement_group_id": batch.procurement_group_id,
                "items_count": len(payload["items"]),
            },
        )
        return batch

    @transaction.atomic
    def create_purchase_order_from_batch(
        self, batch: PurchaseRequestBatch, user: User
    ) -> PurchaseOrder:
        if batch.purchase_order_id:
            return batch.purchase_order
        if not batch.supplier_id:
            raise ValueError("Перед созданием заказа укажите поставщика документа")
        if not batch.items.exists():
            raise ValueError("В документе нет позиций")

        old_batch_status = batch.status
        old_request_status = batch.purchase_request.status
        expected_delivery_date = None
        if batch.purchase_request.due_date:
            expected_delivery_date = timezone.make_aware(
                datetime.combine(batch.purchase_request.due_date, time(hour=18))
            )

        purchase_order = PurchaseOrder.objects.create(
            supplier=batch.supplier,
            shop=batch.purchase_request.shop,
            status=PurchaseOrder.OrderStatus.SENT,
            expected_delivery_date=expected_delivery_date,
            notes=(
                f"Создано из заявки {batch.purchase_request.request_number}, "
                f"документ {batch.batch_number}.\n"
                f"{batch.notes or batch.purchase_request.notes or ''}"
            ).strip(),
            created_by=user,
            approved_by=user,
        )

        total_amount = Decimal("0")
        for batch_item in batch.items.select_related("request_item__item"):
            po_item = PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                item=batch_item.request_item.item,
                ordered_quantity=batch_item.quantity,
                unit_price=batch_item.unit_price,
                notes=batch_item.notes,
            )
            total_amount += po_item.total_price

        purchase_order.subtotal = total_amount
        purchase_order.total_amount = total_amount
        purchase_order.save(update_fields=["subtotal", "total_amount", "updated_at"])

        batch.purchase_order = purchase_order
        batch.status = PurchaseRequestBatch.Status.SENT
        batch.recalculate_totals()
        batch.save(
            update_fields=["purchase_order", "status", "subtotal", "total_amount"]
        )
        self._record_purchase_request_batch_status(
            batch,
            old_batch_status,
            batch.status,
            user,
            f"Создан заказ поставщику {purchase_order.order_number}",
        )

        purchase_request = batch.purchase_request
        if purchase_request.status in {
            PurchaseRequest.Status.APPROVED,
            PurchaseRequest.Status.SPLIT,
        }:
            purchase_request.status = PurchaseRequest.Status.SENT
            purchase_request.save(update_fields=["status", "updated_at"])
            self._record_purchase_request_status(
                purchase_request,
                old_request_status,
                purchase_request.status,
                user,
                f"Создан заказ поставщику {purchase_order.order_number}",
            )

        self.log_purchase_request_event(
            purchase_request,
            PurchaseRequestAuditLog.ActionChoices.ORDER_CREATED,
            f"Создан заказ поставщику {purchase_order.order_number}",
            actor=user,
            batch=batch,
            changes={
                "purchase_order_id": purchase_order.id,
                "purchase_order_number": purchase_order.order_number,
                "total_amount": str(purchase_order.total_amount),
            },
        )

        return purchase_order

    @transaction.atomic
    def receive_purchase_request_batch_full(
        self, batch: PurchaseRequestBatch, user: User
    ) -> dict:
        if not batch.purchase_order_id:
            raise ValueError("Сначала создайте заказ поставщику из документа")

        purchase_order = (
            PurchaseOrder.objects.select_for_update()
            .prefetch_related("items")
            .get(id=batch.purchase_order_id)
        )
        if purchase_order.status == PurchaseOrder.OrderStatus.RECEIVED:
            return {
                "success": True,
                "order_id": purchase_order.id,
                "status": purchase_order.status,
                "received_total": sum(
                    item.received_quantity for item in purchase_order.items.all()
                ),
            }

        receive_items = []
        for order_item in purchase_order.items.all():
            remaining = order_item.ordered_quantity - order_item.received_quantity
            if remaining > 0:
                receive_items.append(
                    {
                        "purchase_order_item_id": order_item.id,
                        "received_quantity": remaining,
                    }
                )

        if not receive_items:
            self._sync_purchase_request_receipt_state(purchase_order, user)
            return {
                "success": True,
                "order_id": purchase_order.id,
                "status": purchase_order.status,
                "received_total": sum(
                    item.received_quantity for item in purchase_order.items.all()
                ),
            }

        return self.receive_purchase_order(purchase_order, receive_items, user)

    @transaction.atomic
    def receive_purchase_request_batch(
        self, batch: PurchaseRequestBatch, items: list[dict], user: User
    ) -> dict:
        if not batch.purchase_order_id:
            raise ValueError("Сначала создайте заказ поставщику из документа")
        if not items:
            raise ValueError("Укажите позиции для приемки")

        purchase_order = (
            PurchaseOrder.objects.select_for_update()
            .prefetch_related("items")
            .get(id=batch.purchase_order_id)
        )
        order_items_by_item_id = {
            order_item.item_id: order_item for order_item in purchase_order.items.all()
        }
        receive_by_order_item: dict[int, int] = {}

        for row in items:
            batch_item = get_object_or_404(
                PurchaseRequestBatchItem.objects.select_related("request_item__item"),
                id=row.get("batch_item_id"),
                batch=batch,
            )
            qty = int(row.get("received_quantity") or 0)
            if qty <= 0:
                continue

            order_item = order_items_by_item_id.get(batch_item.request_item.item_id)
            if not order_item:
                raise ValueError("Позиция отсутствует в заказе поставщику")
            remaining = order_item.ordered_quantity - order_item.received_quantity
            already_planned = receive_by_order_item.get(order_item.id, 0)
            if qty + already_planned > remaining:
                raise ValueError("Нельзя принять больше остатка по документу")

            receive_by_order_item[order_item.id] = already_planned + qty

        receive_items = [
            {
                "purchase_order_item_id": order_item_id,
                "received_quantity": quantity,
            }
            for order_item_id, quantity in receive_by_order_item.items()
        ]
        if not receive_items:
            raise ValueError("Укажите количество больше нуля")

        return self.receive_purchase_order(purchase_order, receive_items, user)

    def _sync_purchase_request_receipt_state(
        self, purchase_order: PurchaseOrder, user: User | None = None
    ) -> None:
        batch = getattr(purchase_order, "purchase_request_batch", None)
        if not batch:
            return

        purchase_request = batch.purchase_request
        for batch_item in batch.items.select_related("request_item__item"):
            request_filter = "purchase_order__purchase_request_batch__purchase_request"
            received = (
                PurchaseOrderItem.objects.filter(
                    **{request_filter: purchase_request},
                    item=batch_item.request_item.item,
                ).aggregate(total=Sum("received_quantity"))["total"]
                or 0
            )
            batch_item.request_item.received_quantity = min(
                int(received), batch_item.request_item.approved_quantity
            )
            batch_item.request_item.save(update_fields=["received_quantity"])

        current_order_items = {
            order_item.item_id: order_item.received_quantity
            for order_item in PurchaseOrderItem.objects.filter(
                purchase_order=purchase_order
            )
        }
        batch_items = list(batch.items.select_related("request_item"))
        batch_total = sum(item.quantity for item in batch_items)
        batch_received = sum(
            min(current_order_items.get(item.request_item.item_id, 0), item.quantity)
            for item in batch_items
        )
        old_batch_status = batch.status
        if batch_received <= 0:
            batch.status = PurchaseRequestBatch.Status.SENT
        elif batch_received < batch_total:
            batch.status = PurchaseRequestBatch.Status.PARTIALLY_RECEIVED
        else:
            batch.status = PurchaseRequestBatch.Status.RECEIVED
        batch.save(update_fields=["status"])
        self._record_purchase_request_batch_status(
            batch,
            old_batch_status,
            batch.status,
            user,
            f"Приемка по заказу {purchase_order.order_number}",
        )

        old_request_status = purchase_request.status
        request_items = list(purchase_request.items.all())
        request_total = sum(
            item.approved_quantity or item.requested_quantity for item in request_items
        )
        request_received = sum(item.received_quantity for item in request_items)
        if request_received <= 0:
            purchase_request.status = PurchaseRequest.Status.SENT
        elif request_received < request_total:
            purchase_request.status = PurchaseRequest.Status.PARTIALLY_RECEIVED
        else:
            purchase_request.status = PurchaseRequest.Status.RECEIVED
        purchase_request.save(update_fields=["status", "updated_at"])
        self._record_purchase_request_status(
            purchase_request,
            old_request_status,
            purchase_request.status,
            user,
            f"Приемка по заказу {purchase_order.order_number}",
        )
        if (
            old_batch_status != batch.status
            or old_request_status != purchase_request.status
        ):
            self.log_purchase_request_event(
                purchase_request,
                PurchaseRequestAuditLog.ActionChoices.RECEIVED,
                f"Принята поставка по документу {batch.batch_number}",
                actor=user,
                batch=batch,
                changes={
                    "purchase_order_id": purchase_order.id,
                    "purchase_order_number": purchase_order.order_number,
                    "batch_status": batch.status,
                    "request_status": purchase_request.status,
                },
            )

    def find_item_by_barcode(self, barcode: str) -> InventoryItem | None:
        # Только таблица мульти-ШК
        ib = (
            InventoryItemBarcode.objects.select_related("item")
            .filter(barcode=barcode, item__is_active=True)
            .first()
        )
        return ib.item if ib else None

    def _resolve_item(self, entry: dict) -> InventoryItem | None:
        """Определить товар по item_id или barcode"""
        if entry.get("item_id"):
            return get_object_or_404(InventoryItem, id=entry["item_id"], is_active=True)
        if entry.get("barcode"):
            return self.find_item_by_barcode(entry["barcode"])
        return None

    @transaction.atomic
    def receive_items_ad_hoc(
        self, shop, user: User, items: list[dict], common_notes: str = ""
    ) -> dict:
        """
        Приемка без заказа поставщику.
        items: [{"item_id": 1, "barcode": "...", "quantity": 50, ...}]
        """
        results = []
        ok = 0
        for row in items:
            item = self._resolve_item(row)
            if not item:
                results.append({"ok": False, "error": "Товар не найден", "entry": row})
                continue
            qty = int(row.get("quantity", 0))
            if qty <= 0:
                results.append(
                    {
                        "ok": False,
                        "error": "Количество должно быть > 0",
                        "item_id": item.id,
                    }
                )
                continue

            # Баланс с блокировкой
            balance, _ = StockBalance.objects.select_for_update().get_or_create(
                shop=shop,
                item=item,
                defaults={
                    "quantity": 0,
                    "reserved_quantity": 0,
                    "available_quantity": 0,
                },
            )

            # Лог (опциональный)
            if row.get("barcode"):
                BarcodeScanEvent.objects.create(
                    barcode=row["barcode"],
                    item=item,
                    shop=shop,
                    user=user,
                    context=BarcodeScanEvent.ScanContext.INVENTORY,
                    quantity=qty,
                    notes=row.get("notes", ""),
                )

            movement = self.create_movement(
                stock_balance_id=balance.id,
                movement_type=StockMovement.MovementType.RECEIPT,
                quantity_change=qty,
                notes=(row.get("notes") or common_notes or "Приемка без заказа"),
                user=user,
                cost_per_unit=Decimal(str(row.get("cost_per_unit")))
                if row.get("cost_per_unit") is not None
                else None,
            )
            # Лог себестоимости (если передан cost_per_unit)
            if row.get("cost_per_unit") is not None:
                InventoryItemCostHistory.objects.create(
                    item=item,
                    shop=shop,
                    source_type=InventoryItemCostHistory.SourceType.AD_HOC,
                    source_id=None,
                    cost_per_unit=Decimal(str(row["cost_per_unit"])),
                    quantity=qty,
                    received_at=timezone.now(),
                    notes=row.get("notes", "") or common_notes or "",
                )
            ok += 1
            results.append(
                {
                    "ok": True,
                    "item_id": item.id,
                    "name": item.name,
                    "quantity_added": qty,
                    "new_quantity": movement.quantity_after,
                }
            )

        return {
            "success": ok == len(items),
            "processed": len(items),
            "ok": ok,
            "results": results,
        }

    @transaction.atomic
    def adjust_items_ad_hoc(
        self, shop, user: User, items: list[dict], common_notes: str = ""
    ) -> dict:
        """
        Корректировка/инвентаризация произвольным списком.
        items: [{"item_id": 1, "barcode": "...", "quantity_change": -5, ...}]
        """
        results = []
        ok = 0
        for row in items:
            item = self._resolve_item(row)
            if not item:
                results.append({"ok": False, "error": "Товар не найден", "entry": row})
                continue
            qchg = int(row.get("quantity_change", 0))
            if qchg == 0:
                results.append(
                    {
                        "ok": False,
                        "error": "Изменение должно быть != 0",
                        "item_id": item.id,
                    }
                )
                continue

            balance, _ = StockBalance.objects.select_for_update().get_or_create(
                shop=shop,
                item=item,
                defaults={
                    "quantity": 0,
                    "reserved_quantity": 0,
                    "available_quantity": 0,
                },
            )
            after = balance.quantity + qchg
            if not item.allow_negative_stock and after < 0:
                results.append(
                    {"ok": False, "error": "Недостаточно остатка", "item_id": item.id}
                )
                continue

            # Лог (опциональный)
            if row.get("barcode"):
                BarcodeScanEvent.objects.create(
                    barcode=row["barcode"],
                    item=item,
                    shop=shop,
                    user=user,
                    context=BarcodeScanEvent.ScanContext.INVENTORY,
                    quantity=qchg,
                    notes=row.get("notes", ""),
                )

            movement = self.create_movement(
                stock_balance_id=balance.id,
                movement_type=StockMovement.MovementType.ADJUSTMENT,
                quantity_change=qchg,
                notes=(row.get("notes") or common_notes or "Корректировка"),
                user=user,
            )
            ok += 1
            results.append(
                {
                    "ok": True,
                    "item_id": item.id,
                    "name": item.name,
                    "quantity_change": qchg,
                    "new_quantity": movement.quantity_after,
                }
            )

        return {
            "success": ok == len(items),
            "processed": len(items),
            "ok": ok,
            "results": results,
        }

    @transaction.atomic
    def create_movement(
        self,
        stock_balance_id: int,
        movement_type: str,
        quantity_change: int,
        notes: str,
        user: User,
        repair_order_id: int = None,
        purchase_order_id: int = None,
        reference_number: str = "",
        cost_per_unit: Decimal | None = None,
    ) -> StockMovement:
        # блокируем строку остатка
        balance = StockBalance.objects.select_for_update().get(id=stock_balance_id)
        before = balance.quantity
        after = before + quantity_change

        if not balance.item.allow_negative_stock and after < 0:
            raise ValueError("Недостаточно остатка (отрицательный остаток запрещен)")

        balance.quantity = after
        balance.save(
            update_fields=[
                "quantity",
                "reserved_quantity",
                "available_quantity",
                "last_movement_date",
            ]
        )

        movement = StockMovement.objects.create(
            stock_balance=balance,
            movement_type=movement_type,
            quantity_before=before,
            quantity_change=quantity_change,
            quantity_after=after,
            notes=notes or "",
            repair_order_id=repair_order_id,
            purchase_order_id=purchase_order_id,
            reference_number=reference_number or "",
            cost_per_unit=cost_per_unit,
            created_by=user,
        )
        return movement

    @transaction.atomic
    def receive_purchase_order(
        self, purchase_order: PurchaseOrder, received_items: list[dict], user: User
    ):
        if purchase_order.status in ["cancelled", "received"]:
            raise ValueError("Заказ уже получен или отменен")

        # создаем движения прихода по каждой позиции
        for item in received_items:
            po_item = get_object_or_404(
                PurchaseOrderItem,
                id=item["purchase_order_item_id"],
                purchase_order=purchase_order,
            )
            qty = int(item.get("received_quantity", 0))
            if qty <= 0:
                continue
            remaining = po_item.ordered_quantity - po_item.received_quantity
            if qty > remaining:
                raise ValueError("Нельзя принять больше заказанного количества")

            # Обновляем полученное количество
            po_item.received_quantity = (po_item.received_quantity or 0) + qty
            po_item.save(update_fields=["received_quantity", "total_price"])

            # Обновляем остаток (создать/найти StockBalance)
            balance, _ = StockBalance.objects.select_for_update().get_or_create(
                shop=purchase_order.shop,
                item=po_item.item,
                defaults={
                    "quantity": 0,
                    "reserved_quantity": 0,
                    "available_quantity": 0,
                },
            )

            self.create_movement(
                stock_balance_id=balance.id,
                movement_type=StockMovement.MovementType.RECEIPT,
                quantity_change=qty,
                notes=f"Приемка по {purchase_order.order_number}",
                user=user,
                purchase_order_id=purchase_order.id,
                reference_number=purchase_order.order_number,
                cost_per_unit=po_item.unit_price,
            )
            InventoryItemCostHistory.objects.create(
                item=po_item.item,
                shop=purchase_order.shop,
                source_type=InventoryItemCostHistory.SourceType.PO,
                source_id=purchase_order.id,
                cost_per_unit=po_item.unit_price,
                quantity=qty,
                received_at=timezone.now(),
                notes=f"PO {purchase_order.order_number}",
            )

        # Обновление статуса заказа поставщику
        totals = PurchaseOrderItem.objects.filter(
            purchase_order=purchase_order
        ).aggregate(
            total_ordered=Sum("ordered_quantity"),
            total_received=Sum("received_quantity"),
        )
        total_ordered = totals["total_ordered"] or 0
        total_received = totals["total_received"] or 0
        if total_received == 0:
            purchase_order.status = PurchaseOrder.OrderStatus.SENT
        elif total_received < total_ordered:
            purchase_order.status = PurchaseOrder.OrderStatus.PARTIALLY_RECEIVED
        else:
            purchase_order.status = PurchaseOrder.OrderStatus.RECEIVED

        purchase_order.actual_delivery_date = timezone.now()
        purchase_order.save(update_fields=["status", "actual_delivery_date"])
        self._sync_purchase_request_receipt_state(purchase_order, user)

        return {
            "success": True,
            "order_id": purchase_order.id,
            "status": purchase_order.status,
            "received_total": total_received,
        }

    def scan_barcode(
        self,
        barcode: str,
        shop,
        user,
        context: str = "pos",
        quantity: int = 1,
        notes: str = "",
    ) -> dict:
        item = self.find_item_by_barcode(barcode)
        BarcodeScanEvent.objects.create(
            barcode=barcode,
            item=item,
            shop=shop,
            user=user,
            context=context,
            quantity=quantity,
            notes=notes,
        )
        if not item:
            return {"found": False, "error": "Товар с таким штрихкодом не найден"}

        balance = StockBalance.objects.filter(shop=shop, item=item).first()
        available = balance.available_quantity if balance else 0
        return {
            "found": True,
            "item_id": item.id,
            "name": item.name,
            "sku": item.sku,
            "barcode": barcode,  # показываем отсканированный ШК
            "price": float(item.selling_price),
            "available_quantity": int(available),
            "unit": item.unit,
        }

    @transaction.atomic
    def start_sale(self, shop, cashier, customer=None, notes: str = "") -> RetailSale:
        sale = RetailSale.objects.create(
            shop=shop, cashier=cashier, customer=customer, notes=notes
        )
        return sale

    @transaction.atomic
    def add_item_to_sale(
        self, sale: RetailSale, item: InventoryItem, quantity: int = 1
    ):
        item_line, created = RetailSaleItem.objects.get_or_create(
            sale=sale,
            item=item,
            defaults={
                "quantity": 0,
                "unit_price": item.selling_price,
                "total_price": 0,
            },
        )
        item_line.quantity += max(1, quantity)
        item_line.unit_price = item.selling_price
        item_line.save()

        # Обновим суммы продажи
        subtotal = sale.items.aggregate(s=Sum("total_price"))["s"] or Decimal("0")
        sale.subtotal = subtotal
        sale.save(
            update_fields=["subtotal", "total_amount", "updated_at"]
            if hasattr(sale, "updated_at")
            else ["subtotal", "total_amount"]
        )

        return item_line

    @transaction.atomic
    def finalize_sale(self, sale: RetailSale, user):
        if sale.status != RetailSale.Status.DRAFT:
            raise ValueError("Продажа уже завершена или отменена")

        # Списываем остатки
        for line in sale.items.select_related("item"):
            # Найти/заблокировать остаток
            balance, _ = StockBalance.objects.select_for_update().get_or_create(
                shop=sale.shop,
                item=line.item,
                defaults={
                    "quantity": 0,
                    "reserved_quantity": 0,
                    "available_quantity": 0,
                },
            )
            # Проверка
            qty_change = -int(line.quantity)
            after = balance.quantity + qty_change
            if not line.item.allow_negative_stock and after < 0:
                raise ValueError(
                    f"Недостаточно остатка для {line.item.name} "
                    f"(доступно {balance.available_quantity})"
                )

            # Движение
            self.create_movement(
                stock_balance_id=balance.id,
                movement_type=StockMovement.MovementType.SHIPMENT,
                quantity_change=qty_change,
                notes=f"POS продажа {sale.sale_number}",
                user=user,
            )

        from django.utils import timezone

        sale.status = RetailSale.Status.COMPLETED
        sale.completed_at = timezone.now()
        sale.save(update_fields=["status", "completed_at"])

        return {
            "success": True,
            "sale_id": sale.id,
            "sale_number": sale.sale_number,
            "total": float(sale.total_amount),
        }

    @transaction.atomic
    def inventory_adjustment_by_scan(
        self, shop, user, barcode: str, quantity_change: int, notes: str = ""
    ):
        """
        Складская операция по скану (корректировка/инвентаризация).
        """
        item = self.find_item_by_barcode(barcode)
        if not item:
            return {"found": False, "error": "Товар с таким штрихкодом не найден"}

        balance, _ = StockBalance.objects.select_for_update().get_or_create(
            shop=shop,
            item=item,
            defaults={"quantity": 0, "reserved_quantity": 0, "available_quantity": 0},
        )
        after = balance.quantity + quantity_change
        if not item.allow_negative_stock and after < 0:
            raise ValueError("Недостаточно остатка (отрицательный остаток запрещен)")

        # Лог скана — сохраняем фактически отсканированный ШК
        BarcodeScanEvent.objects.create(
            barcode=barcode,
            item=item,
            shop=shop,
            user=user,
            context=BarcodeScanEvent.ScanContext.INVENTORY,
            quantity=quantity_change,
            notes=notes,
        )

        self.create_movement(
            stock_balance_id=balance.id,
            movement_type=StockMovement.MovementType.ADJUSTMENT,
            quantity_change=quantity_change,
            notes=notes or "Корректировка по скану",
            user=user,
        )
        return {
            "success": True,
            "item_id": item.id,
            "new_quantity": after,
        }

    # ---------- Аггрегации ----------
    def get_stock_dashboard(self, user: User, current_shop=None) -> dict:
        qs = StockBalance.objects.select_related("shop", "item", "item__category")
        if current_shop:
            qs = qs.filter(shop=current_shop)
        else:
            qs = qs.filter(shop__in=user.get_available_shops())

        # Totals
        totals_q = qs.aggregate(
            total_quantity=Sum("quantity"),
            low_stock_count=Count(
                "id", filter=Q(available_quantity__lte=F("min_quantity"))
            ),
        )
        # total SKUs (уникальные товары, у которых есть остатки в доступных магазинах)
        total_skus = qs.values("item_id").distinct().count()

        # by shop
        by_shop = (
            qs.values("shop_id", "shop__name")
            .annotate(
                total_quantity=Sum("quantity"),
                low_stock_count=Count(
                    "id", filter=Q(available_quantity__lte=F("min_quantity"))
                ),
            )
            .order_by("shop__name")
        )

        # by category
        by_category = (
            qs.values("item__category_id", "item__category__name")
            .annotate(
                total_quantity=Sum("quantity"),
                low_stock_count=Count(
                    "id", filter=Q(available_quantity__lte=F("min_quantity"))
                ),
            )
            .order_by("item__category__name")
        )

        return {
            "totals": {
                "total_skus": total_skus,
                "total_quantity": int(totals_q["total_quantity"] or 0),
                "low_stock_count": int(totals_q["low_stock_count"] or 0),
            },
            "by_shop": [
                {
                    "shop_id": row["shop_id"],
                    "shop_name": row["shop__name"],
                    "total_quantity": int(row["total_quantity"] or 0),
                    "low_stock_count": int(row["low_stock_count"] or 0),
                }
                for row in by_shop
            ],
            "by_category": [
                {
                    "category_id": row["item__category_id"],
                    "category_name": row["item__category__name"] or "",
                    "total_quantity": int(row["total_quantity"] or 0),
                    "low_stock_count": int(row["low_stock_count"] or 0),
                }
                for row in by_category
            ],
        }

    def get_item_stock_by_code(
        self, user: User, code: str | None, barcode: str | None, current_shop=None
    ) -> dict:
        item = None
        if code:
            item = InventoryItem.objects.filter(
                Q(sku=code) | Q(name__iexact=code), is_active=True
            ).first()
        if not item and barcode:
            ib = (
                InventoryItemBarcode.objects.select_related("item")
                .filter(barcode=barcode, item__is_active=True)
                .first()
            )
            item = ib.item if ib else None

        if not item:
            return {"found": False, "error": "Товар не найден"}

        balances = StockBalance.objects.filter(item=item).select_related("shop")
        if current_shop:
            balances = balances.filter(shop=current_shop)
        else:
            balances = balances.filter(shop__in=user.get_available_shops())

        return {
            "found": True,
            "item_id": item.id,
            "name": item.name,
            "sku": item.sku,
            "barcode": None,  # не используем одиночное поле
            "balances": [
                {
                    "shop_id": b.shop_id,
                    "shop_name": b.shop.name,
                    "quantity": int(b.quantity),
                    "reserved_quantity": int(b.reserved_quantity),
                    "available_quantity": int(b.available_quantity),
                }
                for b in balances
            ],
        }

    # ---------- Быстрое создание товара ----------
    @transaction.atomic
    def quick_create_item(self, data: dict, created_by: User) -> InventoryItem:
        """
        Поддержка списка barcodes в data["barcodes"], поле data["barcode"] опционально.
        """
        sku = data["sku"].strip()
        if InventoryItem.objects.filter(sku=sku).exists():
            raise ValueError("Товар с таким SKU уже существует")

        # игнорируем одиночное barcode как источник «правды»
        # но если пришел barcode отдельно — добавим его в список
        barcodes: list[str] = list({*(data.get("barcodes") or [])})
        single_bc = (data.get("barcode") or "").strip()
        if single_bc:
            barcodes.append(single_bc)
        # нормализуем и удалим пустые
        barcodes = [b.strip() for b in barcodes if b and b.strip()]
        # проверим дубликаты для этого товара позже
        # при желании можно проверить глобальные конфликты (другие товары) — пока
        # не требовалось

        category_id = data.get("category_id")
        if not category_id:
            category_name = (data.get("category_name") or "Запчасти").strip()
            if not category_name:
                category_name = "Запчасти"
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": "Категория для быстрых добавлений"},
            )
            category_id = category.id

        procurement_group = self._resolve_procurement_group_from_payload(data)

        item = InventoryItem.objects.create(
            name=data["name"].strip(),
            sku=sku,
            barcode="",  # одиночное поле не используется
            item_type=data["item_type"],
            category_id=category_id,
            procurement_group=procurement_group,
            description=(data.get("description") or "").strip(),
            purchase_price=Decimal(str(data["purchase_price"])),
            selling_price=Decimal(str(data["selling_price"])),
            unit=(data.get("unit") or "шт"),
            created_by=created_by,
            primary_supplier_id=data.get("primary_supplier_id") or None,
        )

        # создаем мульти-ШК
        for bc in barcodes:
            # разрешаем одинаковый ШК для разных товаров? Требование не обязывает
            # глобальную уникальность.
            InventoryItemBarcode.objects.get_or_create(item=item, barcode=bc)

        return item

    # ---------- Платеж по розничной продаже ----------
    @transaction.atomic
    def finalize_sale_with_payment(
        self,
        sale: RetailSale,
        user: User,
        payment_method_id: int | None,
        cash_register_id: int | None,
        description: str | None = "",
    ) -> tuple[dict, Payment | None]:
        # Завершаем продажу (списывает остатки)
        finalize_res = self.finalize_sale(sale, user)

        payment_obj = None
        if payment_method_id:
            pm = get_object_or_404(PaymentMethod, id=payment_method_id)
            cr = None
            if pm.is_cash and cash_register_id:
                cr = get_object_or_404(CashRegister, id=cash_register_id)

            payment_obj = Payment.objects.create(
                payment_type=Payment.PaymentType.INCOME,
                status=Payment.PaymentStatus.COMPLETED,
                amount=Decimal(str(sale.total_amount)),
                fee_amount=Decimal("0"),
                payment_method=pm,
                cash_register=cr,
                order=None,
                purchase_order=None,
                expense=None,
                description=description
                or f"Оплата розничной продажи {sale.sale_number}",
                reference_number=sale.sale_number,
                payment_date=timezone.now(),
                created_by=user,
            )

            # Обновим кассу при наличной оплате
            if cr:
                cr.cash_balance = cr.cash_balance + sale.total_amount
                cr.save(update_fields=["cash_balance"])

            finalize_res.update(
                {
                    "payment_id": payment_obj.id,
                    "payment_number": payment_obj.payment_number,
                }
            )

        return finalize_res, payment_obj

    def get_reorder_suggestions(self, user: User, current_shop=None) -> list[dict]:
        """
        Предложения на перезаказ: товары, у которых available_quantity <= reorder_point.
        Если есть SupplierItem — используем min_order_qty.
        """
        qs = StockBalance.objects.select_related("item", "shop").filter(
            item__is_active=True,
            available_quantity__lte=F("reorder_point"),
        )
        if current_shop:
            qs = qs.filter(shop=current_shop)
        else:
            qs = qs.filter(shop__in=user.get_available_shops())

        suggestions: list[dict] = []
        for b in qs:
            desired = max(b.max_quantity - b.available_quantity, 0)
            supplier_info = SupplierItem.objects.filter(
                item=b.item, is_preferred=True
            ).first()
            min_order = supplier_info.min_order_qty if supplier_info else 1
            suggested_qty = (
                ((desired + min_order - 1) // min_order) * min_order
                if desired > 0
                else min_order
            )

            suggestions.append(
                {
                    "shop_id": b.shop_id,
                    "shop_name": b.shop.name,
                    "item_id": b.item_id,
                    "sku": b.item.sku,
                    "name": b.item.name,
                    "available_quantity": int(b.available_quantity),
                    "reorder_point": int(b.reorder_point),
                    "min_order_qty": int(min_order),
                    "suggested_qty": int(suggested_qty),
                    "preferred_supplier_id": supplier_info.supplier_id
                    if supplier_info
                    else None,
                }
            )
        # можно отсортировать по наибольшему дефициту
        suggestions.sort(key=lambda x: x["available_quantity"] - x["reorder_point"])
        return suggestions


class InventoryReportService:
    """Отчеты по складу (используется в reports/router)"""

    def get_turnover_report(self, period_days: int, user: User, current_shop=None):
        from django.db.models import Count, Sum
        from django.utils import timezone

        end = timezone.now()
        start = end - timezone.timedelta(days=period_days)

        from .models import StockMovement

        qs = StockMovement.objects.filter(created_at__range=[start, end])
        if current_shop:
            qs = qs.filter(stock_balance__shop=current_shop)
        else:
            available_shops = user.get_available_shops()
            qs = qs.filter(stock_balance__shop__in=available_shops)

        by_item = (
            qs.values("stock_balance__item__name", "stock_balance__item__sku")
            .annotate(
                receipts=Sum("quantity_change", filter=Q(movement_type="receipt")),
                shipments=Sum("quantity_change", filter=Q(movement_type="shipment")),
                movements_count=Count("id"),
            )
            .order_by("-movements_count")
        )

        return {
            "period_days": period_days,
            "items": [
                {
                    "name": row["stock_balance__item__name"],
                    "sku": row["stock_balance__item__sku"],
                    "receipts": int(row["receipts"] or 0),
                    "shipments": int(
                        (row["shipments"] or 0) * -1
                    ),  # расходы отрицательные
                    "movements_count": row["movements_count"],
                }
                for row in by_item
            ],
        }
