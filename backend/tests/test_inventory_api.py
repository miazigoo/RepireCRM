import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from inventory.models import (
    Category,
    InventoryItem,
    InventoryProductGroup,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestAuditLog,
    PurchaseRequestBatch,
    PurchaseRequestBatchStatusHistory,
    PurchaseRequestStatusHistory,
    StockBalance,
    StockMovement,
    Supplier,
)
from shops.models import Shop
from users.models import Permission, Role

User = get_user_model()


class InventoryApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(
            name="Test Shop",
            code="TEST01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        role = Role.objects.create(name="Warehouse", code=Role.RoleType.MANAGER)
        for codename in (
            "inventory.add_item",
            "inventory.add_movement",
            "inventory.add_purchase",
            "inventory.add_purchase_request",
            "inventory.approve_purchase_request",
            "inventory.change_purchase_request",
            "inventory.receive_purchase_orders",
            "inventory.change_item",
            "inventory.view_item",
            "inventory.view_purchase_requests",
            "inventory.view_stock",
            "inventory.view_supplier",
        ):
            permission, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": codename,
                    "category": Permission.PermissionCategory.INVENTORY,
                },
            )
            role.permissions.add(permission)
        self.user = User.objects.create_user(
            username="warehouse-user",
            password="pass12345",
            first_name="Warehouse",
            last_name="User",
            role=role,
            current_shop=self.shop,
        )
        self.user.shops.add(self.shop)

    def auth_headers(self):
        payload = {
            "user_id": self.user.id,
            "username": self.user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_CURRENT_SHOP": str(self.shop.id),
        }

    def test_quick_create_item_accepts_category_name(self):
        response = self.client.post(
            "/api/inventory/items/quick-create",
            data=json.dumps(
                {
                    "name": "Аккумулятор iPhone 15",
                    "sku": "BAT-IP15",
                    "item_type": "component",
                    "category_name": "Аккумуляторы",
                    "purchase_price": 1200,
                    "selling_price": 2400,
                    "unit": "шт",
                    "barcodes": ["2000000000011"],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertEqual(payload["sku"], "BAT-IP15")
        self.assertTrue(Category.objects.filter(name="Аккумуляторы").exists())
        self.assertTrue(InventoryItem.objects.filter(sku="BAT-IP15").exists())

    def test_inventory_items_include_stock_display_fields(self):
        category = Category.objects.create(name="Аксессуары")
        item = InventoryItem.objects.create(
            name="Чехол MagSafe",
            sku="CASE-MAG",
            item_type="accessory",
            category=category,
            purchase_price=400,
            selling_price=1200,
            created_by=self.user,
        )
        balance, _ = StockBalance.objects.get_or_create(
            shop=self.shop,
            item=item,
        )
        balance.quantity = 1
        balance.min_quantity = 2
        balance.save(
            update_fields=[
                "quantity",
                "reserved_quantity",
                "available_quantity",
                "min_quantity",
                "last_movement_date",
            ]
        )

        response = self.client.get(
            "/api/inventory/items",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        result = payload["items"][0]
        self.assertEqual(result["sku"], "CASE-MAG")
        self.assertEqual(result["total_stock"], 1)
        self.assertEqual(result["min_quantity"], 2)
        self.assertEqual(result["stock_status"], "low_stock")
        self.assertIsNotNone(result["last_movement_date"])

    def test_update_inventory_item_updates_card_and_current_shop_stock(self):
        category = Category.objects.create(name="Аксессуары")
        supplier = Supplier.objects.create(name="Демо поставщик")
        item = InventoryItem.objects.create(
            name="Чехол старый",
            sku="CASE-OLD",
            item_type="accessory",
            category=category,
            purchase_price=300,
            selling_price=900,
            created_by=self.user,
        )
        balance, _ = StockBalance.objects.get_or_create(shop=self.shop, item=item)
        balance.quantity = 1
        balance.min_quantity = 2
        balance.save()

        response = self.client.put(
            f"/api/inventory/items/{item.id}",
            data=json.dumps(
                {
                    "name": "Чехол прозрачный",
                    "sku": "CASE-CLEAR",
                    "item_type": "accessory",
                    "category_name": "Чехлы",
                    "primary_supplier_id": supplier.id,
                    "stock_quantity": 7,
                    "min_quantity": 3,
                    "purchase_price": 350,
                    "selling_price": 1100,
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        item.refresh_from_db()
        balance.refresh_from_db()
        self.assertEqual(item.name, "Чехол прозрачный")
        self.assertEqual(item.sku, "CASE-CLEAR")
        self.assertEqual(item.category.name, "Чехлы")
        self.assertEqual(item.primary_supplier_id, supplier.id)
        self.assertEqual(balance.quantity, 7)
        self.assertEqual(balance.min_quantity, 3)
        self.assertTrue(
            StockMovement.objects.filter(
                stock_balance=balance,
                movement_type=StockMovement.MovementType.ADJUSTMENT,
                quantity_change=6,
            ).exists()
        )

    def test_create_purchase_order_accepts_legacy_purchase_permission(self):
        category = Category.objects.create(name="Дисплеи")
        item = InventoryItem.objects.create(
            name="Дисплей iPhone 15",
            sku="LCD-IP15",
            item_type="component",
            category=category,
            purchase_price=3000,
            selling_price=6000,
            created_by=self.user,
        )

        response = self.client.post(
            "/api/inventory/purchase-orders",
            data=json.dumps(
                {
                    "supplier_name": "Основной поставщик",
                    "items": [
                        {
                            "item_id": item.id,
                            "quantity": 2,
                            "unit_price": 3000,
                        }
                    ],
                    "notes": "Срочная закупка",
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        order = PurchaseOrder.objects.get()
        order_item = PurchaseOrderItem.objects.get(purchase_order=order)
        self.assertEqual(order.supplier.name, "Основной поставщик")
        self.assertEqual(order_item.ordered_quantity, 2)
        self.assertEqual(float(order.total_amount), 6000.0)

    def test_purchase_request_can_be_split_and_exported_to_pdf(self):
        category = Category.objects.create(name="Комплектующие")
        group = InventoryProductGroup.objects.create(name="Дисплейные модули")
        supplier_one = Supplier.objects.create(name="Поставщик экранов")
        supplier_two = Supplier.objects.create(name="Поставщик АКБ")
        display = InventoryItem.objects.create(
            name="Дисплей iPhone 15",
            sku="LCD-IP15",
            item_type="component",
            category=category,
            procurement_group=group,
            primary_supplier=supplier_one,
            purchase_price=3000,
            selling_price=6000,
            created_by=self.user,
        )
        battery = InventoryItem.objects.create(
            name="Аккумулятор iPhone 15",
            sku="BAT-IP15",
            item_type="component",
            category=category,
            primary_supplier=supplier_two,
            purchase_price=1200,
            selling_price=2600,
            created_by=self.user,
        )

        response = self.client.post(
            "/api/inventory/purchase-requests",
            data=json.dumps(
                {
                    "priority": "high",
                    "due_date": "2026-05-25",
                    "notes": "Подготовить закупку к пятнице",
                    "items": [
                        {"item_id": display.id, "quantity": 2},
                        {
                            "item_id": battery.id,
                            "quantity": 3,
                            "procurement_group_name": "Аккумуляторы",
                        },
                    ],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        purchase_request = PurchaseRequest.objects.get()
        self.assertEqual(purchase_request.status, PurchaseRequest.Status.SUBMITTED)
        self.assertEqual(purchase_request.items.count(), 2)
        self.assertEqual(float(purchase_request.total_amount), 9600.0)

        split_response = self.client.post(
            f"/api/inventory/purchase-requests/{purchase_request.id}/split",
            data=json.dumps({"mode": "supplier_group", "rebuild": True}),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(split_response.status_code, 200, split_response.content)
        purchase_request.refresh_from_db()
        self.assertEqual(purchase_request.status, PurchaseRequest.Status.SPLIT)
        self.assertEqual(PurchaseRequestBatch.objects.count(), 2)

        pdf_response = self.client.get(
            f"/api/inventory/purchase-requests/{purchase_request.id}/pdf",
            **self.auth_headers(),
        )
        self.assertEqual(pdf_response.status_code, 200, pdf_response.content)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertGreater(len(pdf_response.content), 1000)

        batch = PurchaseRequestBatch.objects.first()
        batch_pdf_url = (
            f"/api/inventory/purchase-requests/{purchase_request.id}"
            f"/batches/{batch.id}/pdf"
        )
        batch_pdf_response = self.client.get(
            batch_pdf_url,
            **self.auth_headers(),
        )
        self.assertEqual(
            batch_pdf_response.status_code, 200, batch_pdf_response.content
        )
        self.assertEqual(batch_pdf_response["Content-Type"], "application/pdf")

        order_url = (
            f"/api/inventory/purchase-requests/{purchase_request.id}"
            f"/batches/{batch.id}/purchase-order"
        )
        order_response = self.client.post(
            order_url,
            data=json.dumps({}),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(order_response.status_code, 201, order_response.content)
        purchase_order = PurchaseOrder.objects.get(id=order_response.json()["order_id"])
        batch.refresh_from_db()
        self.assertEqual(batch.purchase_order_id, purchase_order.id)
        self.assertEqual(batch.status, PurchaseRequestBatch.Status.SENT)

        edit_item_url = (
            f"/api/inventory/purchase-requests/{purchase_request.id}"
            f"/items/{purchase_request.items.first().id}"
        )
        edit_after_order_response = self.client.patch(
            edit_item_url,
            data=json.dumps({"approved_quantity": 1}),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(edit_after_order_response.status_code, 400)

        resplit_after_order_response = self.client.post(
            f"/api/inventory/purchase-requests/{purchase_request.id}/split",
            data=json.dumps({"mode": "supplier_group", "rebuild": True}),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(resplit_after_order_response.status_code, 400)

        batch_item = batch.items.first()
        receive_url = (
            f"/api/inventory/purchase-requests/{purchase_request.id}"
            f"/batches/{batch.id}/receive"
        )
        partial_receive_response = self.client.post(
            receive_url,
            data=json.dumps(
                {
                    "items": [
                        {
                            "batch_item_id": batch_item.id,
                            "received_quantity": 1,
                        }
                    ]
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(
            partial_receive_response.status_code,
            200,
            partial_receive_response.content,
        )
        batch.refresh_from_db()
        purchase_request.refresh_from_db()
        purchase_order.refresh_from_db()
        self.assertEqual(batch.status, PurchaseRequestBatch.Status.PARTIALLY_RECEIVED)
        self.assertEqual(
            purchase_order.status, PurchaseOrder.OrderStatus.PARTIALLY_RECEIVED
        )
        self.assertEqual(
            purchase_request.status, PurchaseRequest.Status.PARTIALLY_RECEIVED
        )

        receive_full_url = (
            f"/api/inventory/purchase-requests/{purchase_request.id}"
            f"/batches/{batch.id}/receive-full"
        )
        receive_response = self.client.post(
            receive_full_url,
            data=json.dumps({}),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(receive_response.status_code, 200, receive_response.content)
        batch.refresh_from_db()
        purchase_request.refresh_from_db()
        purchase_order.refresh_from_db()
        order_item = PurchaseOrderItem.objects.get(purchase_order=purchase_order)
        self.assertEqual(batch.status, PurchaseRequestBatch.Status.RECEIVED)
        self.assertEqual(purchase_order.status, PurchaseOrder.OrderStatus.RECEIVED)
        self.assertEqual(order_item.received_quantity, order_item.ordered_quantity)
        self.assertEqual(
            purchase_request.status, PurchaseRequest.Status.PARTIALLY_RECEIVED
        )
        self.assertGreaterEqual(
            PurchaseRequestStatusHistory.objects.filter(
                purchase_request=purchase_request
            ).count(),
            3,
        )
        self.assertTrue(
            PurchaseRequestBatchStatusHistory.objects.filter(
                batch=batch,
                new_status=PurchaseRequestBatch.Status.RECEIVED,
            ).exists()
        )
        self.assertTrue(
            PurchaseRequestAuditLog.objects.filter(
                purchase_request=purchase_request,
                action=PurchaseRequestAuditLog.ActionChoices.ORDER_CREATED,
            ).exists()
        )

        timeline_response = self.client.get(
            f"/api/inventory/purchase-requests/{purchase_request.id}/timeline",
            **self.auth_headers(),
        )
        self.assertEqual(timeline_response.status_code, 200, timeline_response.content)
        timeline = timeline_response.json()
        actions = {event.get("action") for event in timeline}
        event_types = {event.get("event_type") for event in timeline}
        self.assertIn("received", actions)
        self.assertIn("pdf_downloaded", actions)
        self.assertIn("request_status", event_types)
        self.assertIn("batch_status", event_types)

    def test_purchase_request_manual_batch_respects_remaining_quantity(self):
        supplier = Supplier.objects.create(name="Ручной поставщик")
        category = Category.objects.create(name="Комплектующие")
        item = InventoryItem.objects.create(
            name="Дисплейный модуль",
            sku="LCD-MANUAL",
            item_type="component",
            category=category,
            primary_supplier=supplier,
            purchase_price=1700,
            selling_price=3400,
            created_by=self.user,
        )
        create_response = self.client.post(
            "/api/inventory/purchase-requests",
            data=json.dumps(
                {
                    "priority": "normal",
                    "due_date": "2026-06-01",
                    "items": [
                        {
                            "item_id": item.id,
                            "quantity": 5,
                            "supplier_id": supplier.id,
                        }
                    ],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(create_response.status_code, 201, create_response.content)
        purchase_request = PurchaseRequest.objects.get(
            request_number=create_response.json()["request_number"]
        )
        request_item = purchase_request.items.get()

        list_response = self.client.get(
            "/api/inventory/purchase-requests",
            data={
                "supplier_id": supplier.id,
                "status": PurchaseRequest.Status.SUBMITTED,
                "due_from": "2026-05-30",
                "due_to": "2026-06-05",
                "search": "LCD",
            },
            **self.auth_headers(),
        )
        self.assertEqual(list_response.status_code, 200, list_response.content)
        self.assertEqual(len(list_response.json()["items"]), 1)

        batch_response = self.client.post(
            f"/api/inventory/purchase-requests/{purchase_request.id}/batches",
            data=json.dumps(
                {
                    "supplier_id": supplier.id,
                    "title": "Первая партия",
                    "items": [
                        {
                            "request_item_id": request_item.id,
                            "quantity": 2,
                        }
                    ],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(batch_response.status_code, 201, batch_response.content)
        purchase_request.refresh_from_db()
        self.assertEqual(purchase_request.status, PurchaseRequest.Status.SPLIT)
        self.assertEqual(PurchaseRequestBatch.objects.count(), 1)

        overflow_response = self.client.post(
            f"/api/inventory/purchase-requests/{purchase_request.id}/batches",
            data=json.dumps(
                {
                    "supplier_id": supplier.id,
                    "items": [
                        {
                            "request_item_id": request_item.id,
                            "quantity": 4,
                        }
                    ],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(overflow_response.status_code, 400)

    def test_purchase_request_status_endpoint_blocks_internal_and_terminal_statuses(
        self,
    ):
        category = Category.objects.create(name="Комплектующие")
        item = InventoryItem.objects.create(
            name="Камера iPhone 15",
            sku="CAM-IP15",
            item_type="component",
            category=category,
            purchase_price=2100,
            selling_price=4200,
            created_by=self.user,
        )
        create_response = self.client.post(
            "/api/inventory/purchase-requests",
            data=json.dumps(
                {
                    "priority": "normal",
                    "items": [
                        {
                            "item_id": item.id,
                            "quantity": 2,
                        }
                    ],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(create_response.status_code, 201, create_response.content)
        purchase_request = PurchaseRequest.objects.get(
            request_number=create_response.json()["request_number"]
        )
        request_item = purchase_request.items.get()

        internal_status_response = self.client.post(
            f"/api/inventory/purchase-requests/{purchase_request.id}/status",
            data=json.dumps({"status": PurchaseRequest.Status.RECEIVED}),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(internal_status_response.status_code, 400)

        reject_response = self.client.post(
            f"/api/inventory/purchase-requests/{purchase_request.id}/status",
            data=json.dumps(
                {
                    "status": PurchaseRequest.Status.REJECTED,
                    "reason": "Пока не закупаем",
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(reject_response.status_code, 200, reject_response.content)

        edit_rejected_url = (
            f"/api/inventory/purchase-requests/{purchase_request.id}"
            f"/items/{request_item.id}"
        )
        edit_rejected_response = self.client.patch(
            edit_rejected_url,
            data=json.dumps({"approved_quantity": 1}),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(edit_rejected_response.status_code, 400)

        reopen_rejected_response = self.client.post(
            f"/api/inventory/purchase-requests/{purchase_request.id}/status",
            data=json.dumps({"status": PurchaseRequest.Status.APPROVED}),
            content_type="application/json",
            **self.auth_headers(),
        )
        self.assertEqual(reopen_rejected_response.status_code, 400)

    def test_purchase_request_rejects_duplicate_items_without_partial_save(self):
        category = Category.objects.create(name="Комплектующие")
        item = InventoryItem.objects.create(
            name="Шлейф зарядки",
            sku="FLEX-CHARGE",
            item_type="component",
            category=category,
            purchase_price=700,
            selling_price=1400,
            created_by=self.user,
        )

        response = self.client.post(
            "/api/inventory/purchase-requests",
            data=json.dumps(
                {
                    "priority": "normal",
                    "items": [
                        {
                            "item_id": item.id,
                            "quantity": 1,
                        },
                        {
                            "item_id": item.id,
                            "quantity": 2,
                        },
                    ],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("уже добавлен", response.json()["error"])
        self.assertFalse(PurchaseRequest.objects.exists())


class InventoryCrossShopSecurityTests(TestCase):
    """Regression tests for cross-shop IDOR vulnerabilities."""

    def setUp(self):
        self.shop1 = Shop.objects.create(name="Shop 1", code="SH01")
        self.shop2 = Shop.objects.create(name="Shop 2", code="SH02")

        role = Role.objects.create(name="Warehouse", code=Role.RoleType.MANAGER)
        for codename in (
            "inventory.add_movement",
            "inventory.receive_purchase_orders",
            "inventory.receive_purchase",
            "inventory.add_purchase",
        ):
            permission, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": codename,
                    "category": Permission.PermissionCategory.INVENTORY,
                },
            )
            role.permissions.add(permission)

        self.user1 = User.objects.create_user(
            username="shop1user",
            password="pass12345",
            role=role,
            current_shop=self.shop1,
        )
        self.user1.shops.add(self.shop1)

        category = Category.objects.create(name="Parts")
        self.item = InventoryItem.objects.create(
            name="Display",
            sku="LCD-01",
            item_type="component",
            category=category,
            purchase_price=1000,
            selling_price=2000,
            created_by=self.user1,
        )
        self.balance_shop2 = StockBalance.objects.get(
            shop=self.shop2, item=self.item
        )
        self.balance_shop2.quantity = 10
        self.balance_shop2.save()

        supplier = Supplier.objects.create(name="Test Supplier")
        self.po_shop2 = PurchaseOrder.objects.create(
            shop=self.shop2,
            supplier=supplier,
            created_by=self.user1,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=self.po_shop2,
            item=self.item,
            ordered_quantity=5,
            unit_price=1000,
        )

    def _auth_headers(self):
        payload = {
            "user_id": self.user1.id,
            "username": self.user1.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_CURRENT_SHOP": str(self.shop1.id),
        }

    def test_stock_movement_blocked_for_other_shop_balance(self):
        """User from shop1 must not be able to adjust stock in shop2."""
        response = self.client.post(
            "/api/inventory/stock-movement",
            data=json.dumps(
                {
                    "stock_balance_id": self.balance_shop2.id,
                    "movement_type": "adjustment",
                    "quantity_change": -5,
                    "notes": "Cross-shop steal",
                }
            ),
            content_type="application/json",
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 403, response.content)
        self.balance_shop2.refresh_from_db()
        self.assertEqual(self.balance_shop2.quantity, 10)

    def test_purchase_order_receive_blocked_for_other_shop(self):
        """User from shop1 must not be able to receive a purchase order for shop2."""
        response = self.client.post(
            f"/api/inventory/purchase-orders/{self.po_shop2.id}/receive",
            data=json.dumps(
                {
                    "items": [
                        {
                            "item_id": self.item.id,
                            "received_quantity": 5,
                            "unit_price": 1000,
                        }
                    ]
                }
            ),
            content_type="application/json",
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 403, response.content)
