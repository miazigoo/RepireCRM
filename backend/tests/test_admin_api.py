from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order
from shops.models import Shop
from users.models import Role

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
