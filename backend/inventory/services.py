from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from finance.models import CashRegister, Payment, PaymentMethod
from users.models import User

from .models import (
    BarcodeScanEvent,
    InventoryItem,
    InventoryItemBarcode,
    InventoryItemCostHistory,
    PurchaseOrder,
    PurchaseOrderItem,
    RetailSale,
    RetailSaleItem,
    StockBalance,
    StockMovement,
    SupplierItem,
)


class InventoryService:
    """Складские операции"""

    def find_item_by_barcode(self, barcode: str) -> Optional[InventoryItem]:
        # Только таблица мульти-ШК
        ib = (
            InventoryItemBarcode.objects.select_related("item")
            .filter(barcode=barcode, item__is_active=True)
            .first()
        )
        return ib.item if ib else None

    def _resolve_item(self, entry: Dict) -> Optional[InventoryItem]:
        """Определить товар по item_id или barcode"""
        if entry.get("item_id"):
            return get_object_or_404(InventoryItem, id=entry["item_id"], is_active=True)
        if entry.get("barcode"):
            return self.find_item_by_barcode(entry["barcode"])
        return None

    @transaction.atomic
    def receive_items_ad_hoc(
        self, shop, user: User, items: List[Dict], common_notes: str = ""
    ) -> Dict:
        """
        Приемка без заказа поставщику.
        items: [{"item_id": 1, "barcode": "...", "quantity": 50, "cost_per_unit": 100.0, "notes": "..."}, ...]
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
        self, shop, user: User, items: List[Dict], common_notes: str = ""
    ) -> Dict:
        """
        Корректировка/инвентаризация произвольным списком.
        items: [{"item_id": 1, "barcode": "...", "quantity_change": -5, "notes": "..."}, ...]
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
    def get_stock_dashboard(self, user: User) -> Dict:
        qs = StockBalance.objects.select_related("shop", "item", "item__category")
        if not user.is_director:
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
        self, user: User, code: Optional[str], barcode: Optional[str]
    ) -> Dict:
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
        if not user.is_director:
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
    def quick_create_item(self, data: Dict, created_by: User) -> InventoryItem:
        """
        Поддержка списка barcodes в data["barcodes"], поле data["barcode"] опционально.
        """
        sku = data["sku"].strip()
        if InventoryItem.objects.filter(sku=sku).exists():
            raise ValueError("Товар с таким SKU уже существует")

        # игнорируем одиночное поле barcode как источник «правды» — используем barcodes список
        # но если пришел barcode отдельно — добавим его в список
        barcodes: List[str] = list({*(data.get("barcodes") or [])})
        single_bc = (data.get("barcode") or "").strip()
        if single_bc:
            barcodes.append(single_bc)
        # нормализуем и удалим пустые
        barcodes = [b.strip() for b in barcodes if b and b.strip()]
        # проверим дубликаты для этого же товара позже (уникальность пары item+barcode обеспечит БД)
        # при желании можно проверить глобальные конфликты (другие товары) — пока не требовалось

        item = InventoryItem.objects.create(
            name=data["name"].strip(),
            sku=sku,
            barcode="",  # одиночное поле не используется
            item_type=data["item_type"],
            category_id=data["category_id"],
            description=(data.get("description") or "").strip(),
            purchase_price=Decimal(str(data["purchase_price"])),
            selling_price=Decimal(str(data["selling_price"])),
            unit=(data.get("unit") or "шт"),
            created_by=created_by,
            primary_supplier_id=data.get("primary_supplier_id") or None,
        )

        # создаем мульти-ШК
        for bc in barcodes:
            # разрешаем одинаковый ШК для разных товаров? Требование не обязывает глобальную уникальность.
            InventoryItemBarcode.objects.get_or_create(item=item, barcode=bc)

        return item

    # ---------- Платеж по розничной продаже ----------
    @transaction.atomic
    def finalize_sale_with_payment(
        self,
        sale: RetailSale,
        user: User,
        payment_method_id: Optional[int],
        cash_register_id: Optional[int],
        description: Optional[str] = "",
    ) -> Tuple[Dict, Optional[Payment]]:
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

    def get_reorder_suggestions(self, user: User) -> List[dict]:
        """
        Предложения на перезаказ: товары, у которых available_quantity <= reorder_point.
        Если есть SupplierItem — используем min_order_qty.
        """
        qs = StockBalance.objects.select_related("item", "shop").filter(
            item__is_active=True,
            available_quantity__lte=F("reorder_point"),
        )
        if not user.is_director:
            qs = qs.filter(shop__in=user.get_available_shops())

        suggestions: List[dict] = []
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
