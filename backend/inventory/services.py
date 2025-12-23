from decimal import Decimal
from typing import Dict, List

from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from users.models import User

from .models import (
    BarcodeScanEvent,
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    RetailSale,
    RetailSaleItem,
    StockBalance,
    StockMovement,
)


class InventoryService:
    """Складские операции"""

    def find_item_by_barcode(self, barcode: str) -> InventoryItem | None:
        try:
            return InventoryItem.objects.get(barcode=barcode, is_active=True)
        except InventoryItem.DoesNotExist:
            return None

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
        self, purchase_order: PurchaseOrder, received_items: List[Dict], user: User
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

        # Обновление статуса заказа поставщику
        total_ordered = sum(p.ordered_quantity for p in purchase_order.items.all())
        total_received = sum(p.received_quantity for p in purchase_order.items.all())
        if total_received == 0:
            purchase_order.status = PurchaseOrder.OrderStatus.SENT
        elif total_received < total_ordered:
            purchase_order.status = PurchaseOrder.OrderStatus.PARTIALLY_RECEIVED
        else:
            purchase_order.status = PurchaseOrder.OrderStatus.RECEIVED

        purchase_order.actual_delivery_date = timezone.now()
        purchase_order.save(update_fields=["status", "actual_delivery_date"])

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
        """
        Универсальная обработка скана (POS/склад). Возвращает информацию о товаре.
        """
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

        # Текущий остаток по магазину
        balance = StockBalance.objects.filter(shop=shop, item=item).first()
        available = balance.available_quantity if balance else 0
        return {
            "found": True,
            "item_id": item.id,
            "name": item.name,
            "sku": item.sku,
            "barcode": item.barcode,
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
                    f"Недостаточно остатка для {line.item.name} (доступно {balance.available_quantity})"
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

        # Лог скана
        BarcodeScanEvent.objects.create(
            barcode=item.barcode,
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
            "new_quantity": balance.quantity + quantity_change,
        }


class InventoryReportService:
    """Отчеты по складу (используется в reports/router)"""

    def get_turnover_report(self, period_days: int, user: User):
        from django.db.models import Count, Sum
        from django.utils import timezone

        end = timezone.now()
        start = end - timezone.timedelta(days=period_days)

        from .models import StockMovement

        qs = StockMovement.objects.filter(created_at__range=[start, end])
        if not user.is_director:
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
