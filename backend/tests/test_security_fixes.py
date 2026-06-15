# Tests for Security Fixes - backend/tests/test_security_fixes.py

import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from customers.models import Customer, CustomerShopHistory
from finance.models import Payment, PaymentMethod, PaymentReceipt
from orders.models import Order
from shops.models import Organization, Shop, ShopSettings
from users.models import Permission, Role

User = get_user_model()


class ShopAccessSecurityTests(TestCase):
    """Проверяет что многотенантность работает правильно после исправлений"""

    def setUp(self):
        """Создание тестовых данных"""
        # Две разные лавки
        self.shop1 = Shop.objects.create(name="Shop 1", code="SH01")
        self.shop2 = Shop.objects.create(name="Shop 2", code="SH02")

        # Пользователи с доступом к разным магазинам
        self.user1 = User.objects.create_user(
            username="user1", password="pass123", first_name="User", last_name="One"
        )
        self.user1.shops.add(self.shop1)
        self.user1.current_shop = self.shop1

        self.user2 = User.objects.create_user(
            username="user2", password="pass123", first_name="User", last_name="Two"
        )
        self.user2.shops.add(self.shop2)
        self.user2.current_shop = self.shop2

        role = Role.objects.create(name="Customer Manager", code="manager")
        for codename in (
            "customers.view_customer",
            "customers.change_customer",
            "customers.delete_customer",
        ):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=Permission.PermissionCategory.CUSTOMERS,
            )
            role.permissions.add(permission)
        self.user1.role = role
        self.user2.role = role
        self.user1.save()
        self.user2.save()

        # Клиенты в разных магазинах
        self.customer1 = Customer.objects.create(
            first_name="John", last_name="Doe", phone="+1234567890"
        )
        CustomerShopHistory.objects.create(customer=self.customer1, shop=self.shop1)

        self.customer2 = Customer.objects.create(
            first_name="Jane", last_name="Smith", phone="+9876543210"
        )
        CustomerShopHistory.objects.create(customer=self.customer2, shop=self.shop2)

    def _get_auth_headers(self, user, shop):
        """Генерирует JWT tokens и headers"""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_CURRENT_SHOP": str(shop.id),
        }

    def test_customers_are_shared_between_shops_in_list_endpoint(self):
        """Клиенты общие между филиалами, список не фильтруется по магазину"""
        response = self.client.get(
            "/api/customers/",
            **self._get_auth_headers(self.user1, self.shop1),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        customers = payload["items"] if isinstance(payload, dict) else payload

        customer_ids = [c["id"] for c in customers]
        self.assertIn(self.customer1.id, customer_ids)
        self.assertIn(self.customer2.id, customer_ids)

    def test_customer_detail_is_shared_between_shops(self):
        """Клиент доступен сотруднику другого филиала при наличии прав"""
        response = self.client.get(
            f"/api/customers/{self.customer2.id}",
            **self._get_auth_headers(self.user1, self.shop1),
        )
        self.assertEqual(response.status_code, 200)

    def test_customer_update_is_shared_between_shops(self):
        """Общий клиент редактируется сотрудником другого филиала при наличии прав"""
        response = self.client.put(
            f"/api/customers/{self.customer2.id}",
            data=json.dumps({"first_name": "Updated"}),
            content_type="application/json",
            **self._get_auth_headers(self.user1, self.shop1),
        )
        self.assertEqual(response.status_code, 200)

        self.customer2.refresh_from_db()
        self.assertEqual(self.customer2.first_name, "Updated")

    def test_customer_delete_is_shared_between_shops(self):
        """Общий клиент удаляется сотрудником другого филиала при наличии прав"""
        response = self.client.delete(
            f"/api/customers/{self.customer2.id}",
            **self._get_auth_headers(self.user1, self.shop1),
        )
        self.assertEqual(response.status_code, 200)

        self.assertFalse(Customer.objects.filter(id=self.customer2.id).exists())


class FinanceSecurityTests(TestCase):
    """Проверяет запрет платежей для заказов других магазинов"""

    def setUp(self):
        self.shop1 = Shop.objects.create(name="Shop 1", code="SH01")
        self.shop2 = Shop.objects.create(name="Shop 2", code="SH02")

        # Cashier в shop1
        self.user1 = User.objects.create_user(
            username="cashier1", password="pass123", first_name="Cash", last_name="One"
        )
        self.user1.shops.add(self.shop1)
        self.user1.current_shop = self.shop1
        self.user1.save()

        # Создаем заказ в shop2
        from device.models import Device, DeviceBrand, DeviceModel, DeviceType

        self.customer2 = Customer.objects.create(
            first_name="Customer", last_name="Two", phone="+9999999999"
        )
        self.device_type = DeviceType.objects.create(name="Phone")
        self.device_brand = DeviceBrand.objects.create(name="Apple")
        self.device_model = DeviceModel.objects.create(
            name="iPhone", brand=self.device_brand, device_type=self.device_type
        )
        self.device = Device.objects.create(model=self.device_model)

        self.order_shop2 = Order.objects.create(
            shop=self.shop2,
            customer=self.customer2,
            device=self.device,
            problem_description="Test",
            cost_estimate=1000.00,
            created_by=self.user1,
        )

        # Payment method
        self.payment_method = PaymentMethod.objects.create(name="Cash", is_cash=True)

    def _get_auth_headers(self, user, shop):
        payload = {
            "user_id": user.id,
            "username": user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_CURRENT_SHOP": str(shop.id),
        }

    def test_finance_cannot_access_other_shop_order(self):
        """Cashier из shop1 НЕ должен создать платеж для order в shop2"""
        # Добавим permission
        role = Role.objects.create(name="Cashier", code="cashier")
        permission = Permission.objects.create(
            name="add_payment",
            codename="finance.add_payment",
            category="orders",
        )
        role.permissions.add(permission)
        self.user1.role = role
        self.user1.save()

        response = self.client.post(
            f"/api/finance/order/{self.order_shop2.id}/create",
            data=json.dumps(
                {
                    "amount": "500.00",
                    "payment_method_id": self.payment_method.id,
                    "cash_register_id": 1,
                }
            ),
            content_type="application/json",
            **self._get_auth_headers(self.user1, self.shop1),
        )

        # Должна вернуть 403 Forbidden
        self.assertEqual(response.status_code, 403)


class AuthenticationTests(TestCase):
    """Проверяет что auth endpoints правильно возвращают user с related fields"""

    def setUp(self):
        self.shop = Shop.objects.create(name="Test Shop", code="TEST")
        self.role = Role.objects.create(name="Manager", code="manager")
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            email="test@example.com",
        )
        self.user.role = self.role
        self.user.current_shop = self.shop
        self.user.shops.add(self.shop)
        self.user.save()
        self.permission = Permission.objects.create(
            name="Просмотр всех филиалов",
            codename="reports.view_all_shops",
            category="reports",
        )
        self.role.permissions.add(self.permission)

    def test_login_returns_user_with_role_and_shop(self):
        """Login должен возвращать user с role и current_shop"""
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": "testuser", "password": "testpass123"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("access_token", data)
        self.assertIn("user", data)

        user_data = data["user"]
        self.assertEqual(user_data["username"], "testuser")
        self.assertIsNotNone(user_data["role"])
        self.assertEqual(user_data["role"]["code"], "manager")
        self.assertIn("reports.view_all_shops", user_data["role"]["permission_codes"])
        self.assertIsNotNone(user_data["current_shop"])
        self.assertEqual(user_data["current_shop"]["code"], "TEST")

    def test_login_strips_surrounding_whitespace(self):
        """Случайные пробелы при копипасте логина/пароля не должны ломать вход."""
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": " testuser ", "password": " testpass123 "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["user"]["username"], "testuser")

    def test_get_current_user_includes_related_fields(self):
        """GET /auth/me должен возвращать user с role и current_shop"""
        payload = {
            "user_id": self.user.id,
            "username": self.user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        response = self.client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_CURRENT_SHOP=str(self.shop.id),
        )

        self.assertEqual(response.status_code, 200)
        user_data = response.json()

        self.assertIsNotNone(user_data["role"])
        self.assertEqual(user_data["role"]["code"], "manager")
        self.assertIn("reports.view_all_shops", user_data["role"]["permission_codes"])
        self.assertIsNotNone(user_data["current_shop"])
        self.assertEqual(user_data["current_shop"]["code"], "TEST")

    def test_switch_shop_returns_updated_user(self):
        """POST /auth/switch-shop должен возвращать обновленного user"""
        # Создаем второй магазин
        shop2 = Shop.objects.create(name="Shop 2", code="SH02")
        self.user.shops.add(shop2)
        self.user.save()

        payload = {
            "user_id": self.user.id,
            "username": self.user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        response = self.client.post(
            f"/api/auth/switch-shop/{shop2.id}",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_CURRENT_SHOP=str(self.shop.id),
        )

        self.assertEqual(response.status_code, 200)
        user_data = response.json()

        # Проверяем что current_shop обновлен
        self.assertIsNotNone(user_data["current_shop"])
        self.assertEqual(user_data["current_shop"]["code"], "SH02")
        self.assertIsNotNone(user_data["role"])
        self.assertIn("reports.view_all_shops", user_data["role"]["permission_codes"])


class InventoryCrossShopSecurityTests(TestCase):
    """Cross-shop IDOR regression tests for stock movement and purchase order receipt."""

    def setUp(self):
        from inventory.models import (
            Category,
            InventoryItem,
            PurchaseOrder,
            PurchaseOrderItem,
            StockBalance,
            Supplier,
        )

        self.shop1 = Shop.objects.create(name="Shop 1", code="SH01")
        self.shop2 = Shop.objects.create(name="Shop 2", code="SH02")

        # User belonging only to shop1 with full inventory permissions
        role = Role.objects.create(name="Warehouse", code="warehouse_sec")
        for codename in (
            "inventory.add_movement",
            "inventory.receive_purchase_orders",
        ):
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": codename,
                    "category": Permission.PermissionCategory.INVENTORY,
                },
            )
            role.permissions.add(perm)
        self.user = User.objects.create_user(
            username="shop1-inventory",
            password="pass12345",
            current_shop=self.shop1,
            role=role,
        )
        self.user.shops.add(self.shop1)

        category = Category.objects.create(name="Parts")
        self.item = InventoryItem.objects.create(
            name="Battery",
            sku="BAT-01",
            item_type=InventoryItem.ItemType.COMPONENT,
            category=category,
            purchase_price=Decimal("100"),
            selling_price=Decimal("200"),
            created_by=self.user,
        )
        # StockBalance in shop2 — must NOT be writable by shop1 user
        self.balance_shop2 = StockBalance.objects.create(
            shop=self.shop2,
            item=self.item,
            quantity=10,
            reserved_quantity=0,
            available_quantity=10,
        )

        supplier = Supplier.objects.create(name="Supplier A")
        self.po_shop2 = PurchaseOrder.objects.create(
            shop=self.shop2,
            supplier=supplier,
            order_number="PO-SH02-001",
            status=PurchaseOrder.OrderStatus.SENT,
            created_by=self.user,
        )
        self.po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.po_shop2,
            item=self.item,
            ordered_quantity=5,
            received_quantity=0,
            unit_price=Decimal("100"),
        )

    def _auth_headers(self):
        payload = {
            "user_id": self.user.id,
            "username": self.user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_CURRENT_SHOP": str(self.shop1.id),
        }

    def test_stock_movement_blocked_for_other_shop_balance(self):
        """POST /inventory/stock-movement must reject stock_balance_id from another shop."""
        response = self.client.post(
            "/api/inventory/stock-movement",
            data=json.dumps(
                {
                    "stock_balance_id": self.balance_shop2.id,
                    "movement_type": "adjustment",
                    "quantity_change": 5,
                    "notes": "Cross-shop injection attempt",
                }
            ),
            content_type="application/json",
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 403)
        # Stock balance must remain unchanged
        self.balance_shop2.refresh_from_db()
        self.assertEqual(self.balance_shop2.quantity, 10)

    def test_purchase_order_receipt_blocked_for_other_shop(self):
        """POST /inventory/purchase-orders/{id}/receive must reject cross-shop orders."""
        response = self.client.post(
            f"/api/inventory/purchase-orders/{self.po_shop2.id}/receive",
            data=json.dumps(
                {
                    "items": [
                        {
                            "purchase_order_item_id": self.po_item.id,
                            "received_quantity": 3,
                        }
                    ]
                }
            ),
            content_type="application/json",
            **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 403)
        self.po_item.refresh_from_db()
        self.assertEqual(self.po_item.received_quantity, 0)


class FiscalReceiptPaymentLossTests(TestCase):
    """Regression: ValueError in build_payment_receipt_snapshot must NOT roll back payment."""

    def setUp(self):
        from device.models import Device, DeviceBrand, DeviceModel, DeviceType
        from finance.fiscal_constants import FiscalVatCode

        self.shop = Shop.objects.create(name="Fiscal Shop", code="FISC", currency="RUB")
        organization = Organization.objects.create(name="Fiscal Org")
        ShopSettings.objects.create(
            shop=self.shop,
            organization=organization,
            fiscalization_enabled=True,
            default_service_vat_code=FiscalVatCode.NONE,
        )
        self.user = User.objects.create_user(
            username="cashier-fiscal",
            password="pass12345",
            current_shop=self.shop,
        )
        self.user.shops.add(self.shop)
        self.payment_method = PaymentMethod.objects.create(
            name="Cash", code="cash_fisc", is_cash=True
        )
        brand = DeviceBrand.objects.create(name="Apple")
        device_type = DeviceType.objects.create(name="Phone")
        model = DeviceModel.objects.create(
            brand=brand, device_type=device_type, name="iPhone 15"
        )
        customer = Customer.objects.create(first_name="A", last_name="B", phone="+7000")
        self.device = Device.objects.create(model=model)
        self.order = Order.objects.create(
            shop=self.shop,
            customer=customer,
            device=self.device,
            problem_description="Test",
            cost_estimate=Decimal("5000"),
            created_by=self.user,
        )

    def test_payment_survives_when_receipt_snapshot_raises(self):
        """Payment row must be saved even when build_payment_receipt_snapshot raises."""
        from finance.fiscal_receipts import create_or_update_payment_receipt

        payment = Payment.objects.create(
            payment_type=Payment.PaymentType.INCOME,
            status=Payment.PaymentStatus.COMPLETED,
            amount=Decimal("5000"),
            payment_method=self.payment_method,
            order=self.order,
            payment_date=timezone.now(),
            created_by=self.user,
            fiscal_required=True,
        )

        with patch(
            "finance.fiscal_receipts.build_payment_receipt_snapshot",
            side_effect=ValueError("forced snapshot error"),
        ):
            receipt = create_or_update_payment_receipt(payment)

        # Payment must still exist
        self.assertTrue(Payment.objects.filter(id=payment.id).exists())
        # Receipt must be created with FAILED status
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.status, PaymentReceipt.Status.FAILED)
        self.assertIn("forced snapshot error", receipt.error_message)


@override_settings(YOOKASSA_MOCK=False)
class YooKassaWebhookIPTests(TestCase):
    """X-Forwarded-For spoofing regression tests for YooKassa webhook IP check."""

    def _make_request(self, meta: dict):
        class FakeRequest:
            META = meta

        return FakeRequest()

    def _check_ip(self, meta: dict) -> bool:
        from finance.router import _is_yookassa_ip

        return _is_yookassa_ip(self._make_request(meta))

    def test_valid_yookassa_ip_via_x_real_ip(self):
        self.assertTrue(
            self._check_ip({"HTTP_X_REAL_IP": "185.71.76.1", "REMOTE_ADDR": ""})
        )

    def test_invalid_ip_via_x_real_ip_is_rejected(self):
        self.assertFalse(
            self._check_ip({"HTTP_X_REAL_IP": "1.2.3.4", "REMOTE_ADDR": ""})
        )

    def test_spoofed_xff_first_entry_is_ignored(self):
        """Client-controlled first XFF entry must not grant access."""
        self.assertFalse(
            self._check_ip(
                {
                    "HTTP_X_FORWARDED_FOR": "185.71.76.1, 1.2.3.4",
                    "REMOTE_ADDR": "",
                }
            )
        )

    def test_rightmost_xff_entry_is_trusted(self):
        """Rightmost XFF entry (appended by our nginx) must be used."""
        self.assertTrue(
            self._check_ip(
                {
                    "HTTP_X_FORWARDED_FOR": "1.2.3.4, 185.71.76.1",
                    "REMOTE_ADDR": "",
                }
            )
        )

    def test_x_real_ip_takes_precedence_over_xff(self):
        self.assertFalse(
            self._check_ip(
                {
                    "HTTP_X_REAL_IP": "1.2.3.4",
                    "HTTP_X_FORWARDED_FOR": "185.71.76.1",
                    "REMOTE_ADDR": "",
                }
            )
        )

    def test_no_headers_falls_back_to_remote_addr(self):
        self.assertTrue(self._check_ip({"REMOTE_ADDR": "185.71.76.1"}))
        self.assertFalse(self._check_ip({"REMOTE_ADDR": "1.2.3.4"}))

    @override_settings(YOOKASSA_MOCK=True)
    def test_mock_mode_always_allows(self):
        self.assertTrue(
            self._check_ip({"HTTP_X_REAL_IP": "1.2.3.4", "REMOTE_ADDR": ""})
        )
