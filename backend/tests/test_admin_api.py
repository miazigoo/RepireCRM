import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order
from shops.models import Shop
from users.models import Permission, Role

User = get_user_model()


class AdminApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(
            name="Test Shop",
            code="TEST01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        role = Role.objects.create(name="Director", code=Role.RoleType.DIRECTOR)
        self.user = User.objects.create_user(
            username="admin-user",
            password="pass12345",
            first_name="Admin",
            last_name="User",
            role=role,
            current_shop=self.shop,
            is_director=True,
        )
        self.user.shops.add(self.shop)

        customer = Customer.objects.create(
            first_name="John", last_name="Doe", phone="+79991234567"
        )
        brand = DeviceBrand.objects.create(name="Apple")
        device_type = DeviceType.objects.create(name="Смартфон")
        model = DeviceModel.objects.create(
            brand=brand, device_type=device_type, name="iPhone 15"
        )
        device = Device.objects.create(model=model)
        Order.objects.create(
            shop=self.shop,
            customer=customer,
            device=device,
            problem_description="Нет изображения",
            cost_estimate=5000,
            final_cost=7000,
            created_by=self.user,
        )

    def auth_headers(self):
        return self.auth_headers_for(self.user, self.shop)

    def auth_headers_for(self, user, shop):
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

    def test_admin_statistics_endpoint_returns_dashboard_payload(self):
        response = self.client.get(
            "/api/admin/statistics",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["total_users"], 1)
        self.assertEqual(payload["active_users"], 1)
        self.assertEqual(payload["total_shops"], 1)
        self.assertEqual(payload["active_shops"], 1)
        self.assertEqual(payload["total_orders_today"], 1)
        self.assertEqual(payload["total_revenue_today"], 7000.0)
        self.assertEqual(payload["system_health"], "good")

    def test_admin_management_endpoints_return_lists(self):
        Permission.objects.create(
            name="Просмотр пользователей",
            codename="users.view_user",
            category=Permission.PermissionCategory.USERS,
        )

        endpoints = (
            "/api/admin/users?page=1&page_size=20",
            "/api/admin/users/options",
            "/api/admin/roles",
            "/api/admin/shops",
            "/api/admin/permissions",
        )

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint, **self.auth_headers())

                self.assertEqual(response.status_code, 200, response.content)
                self.assertIsInstance(response.json(), list)

    def test_admin_user_options_returns_lightweight_payload(self):
        response = self.client.get(
            "/api/admin/users/options?limit=10",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        usernames = {item["username"] for item in payload}
        self.assertIn("admin-user", usernames)
        for item in payload:
            self.assertNotIn("role", item)
            self.assertNotIn("shops", item)

    def test_admin_shop_coordinates_roundtrip(self):
        response = self.client.post(
            "/api/admin/shops",
            data=json.dumps(
                {
                    "name": "Map Shop",
                    "code": "MAP01",
                    "city": "Москва",
                    "address": "г. Москва, ул. Тверская, д. 1",
                    "latitude": 55.757969,
                    "longitude": 37.615587,
                    "timezone": "Europe/Moscow",
                    "currency": "RUB",
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertEqual(payload["latitude"], 55.757969)
        self.assertEqual(payload["longitude"], 37.615587)

    def test_permissions_endpoint_returns_human_readable_catalog(self):
        call_command("init_permissions", verbosity=0)

        response = self.client.get("/api/admin/permissions", **self.auth_headers())

        self.assertEqual(response.status_code, 200, response.content)
        permissions = response.json()
        by_code = {permission["code"]: permission for permission in permissions}
        self.assertEqual(
            by_code["users.manage_shop_access"]["name"],
            "Назначать филиалы сотрудникам",
        )
        self.assertEqual(
            by_code["reports.view_all_shops"]["name"],
            "Видеть общую статистику",
        )
        self.assertEqual(by_code["finance.add_payment"]["category_label"], "Финансы")

    def test_delegated_admin_can_assign_only_available_shops(self):
        shop2 = Shop.objects.create(name="Second Shop", code="TEST02")
        target = User.objects.create_user(
            username="target-user",
            password="pass12345",
            first_name="Target",
            last_name="User",
            current_shop=self.shop,
        )
        target.shops.add(self.shop)
        role = Role.objects.create(name="Shop Access Admin", code=Role.RoleType.ADMIN)
        for codename in (
            "users.view_user",
            "users.change_user",
            "users.manage_shop_access",
        ):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=Permission.PermissionCategory.USERS,
            )
            role.permissions.add(permission)
        delegated = User.objects.create_user(
            username="delegated-admin",
            password="pass12345",
            first_name="Delegated",
            last_name="Admin",
            role=role,
            current_shop=self.shop,
        )
        delegated.shops.add(self.shop, shop2)
        self.assertEqual(
            list(target.shops.values_list("id", flat=True)), [self.shop.id]
        )

        response = self.client.put(
            f"/api/admin/users/{target.id}",
            data=json.dumps({"shop_ids": [shop2.id]}),
            content_type="application/json",
            **self.auth_headers_for(delegated, self.shop),
        )

        self.assertEqual(response.status_code, 200, response.content)
        target.refresh_from_db()
        self.assertEqual(list(target.shops.values_list("id", flat=True)), [shop2.id])

    def test_user_without_shop_access_permission_cannot_assign_shops(self):
        shop2 = Shop.objects.create(name="Second Shop", code="TEST02")
        target = User.objects.create_user(
            username="limited-target",
            password="pass12345",
            first_name="Limited",
            last_name="Target",
            current_shop=self.shop,
        )
        target.shops.add(self.shop)
        role = Role.objects.create(name="Limited Admin", code=Role.RoleType.MANAGER)
        for codename in ("users.view_user", "users.change_user"):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=Permission.PermissionCategory.USERS,
            )
            role.permissions.add(permission)
        limited = User.objects.create_user(
            username="limited-admin",
            password="pass12345",
            first_name="Limited",
            last_name="Admin",
            role=role,
            current_shop=self.shop,
        )
        limited.shops.add(self.shop, shop2)

        response = self.client.put(
            f"/api/admin/users/{target.id}",
            data=json.dumps({"shop_ids": [shop2.id]}),
            content_type="application/json",
            **self.auth_headers_for(limited, self.shop),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            list(target.shops.values_list("id", flat=True)), [self.shop.id]
        )
