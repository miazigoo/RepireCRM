# Tests for Security Fixes - backend/tests/test_security_fixes.py

import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer, CustomerShopHistory
from finance.models import PaymentMethod
from orders.models import Order
from shops.models import Shop
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
