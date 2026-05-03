import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from inventory.models import Category, InventoryItem, PurchaseOrder, PurchaseOrderItem
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
            "inventory.add_purchase",
            "inventory.view_item",
            "inventory.view_stock",
            "inventory.view_supplier",
        ):
            role.permissions.add(
                Permission.objects.create(
                    name=codename,
                    codename=codename,
                    category=Permission.PermissionCategory.INVENTORY,
                )
            )
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
