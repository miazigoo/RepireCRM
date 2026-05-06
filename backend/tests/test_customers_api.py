from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer, CustomerShopHistory
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order
from shops.models import Shop

User = get_user_model()


class CustomersApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(
            name="Main Shop",
            code="MAIN01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        self.other_shop = Shop.objects.create(
            name="Other Shop",
            code="OTHER01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        self.user = User.objects.create_user(
            username="customers-user",
            password="pass12345",
            first_name="Customer",
            last_name="Manager",
            current_shop=self.shop,
            is_superuser=True,
        )
        self.user.shops.add(self.shop, self.other_shop)

        self.customer = Customer.objects.create(
            first_name="Иван",
            last_name="Иванов",
            phone="+79990000001",
            created_by=self.user,
        )
        CustomerShopHistory.objects.create(customer=self.customer, shop=self.shop)

        self.other_customer = Customer.objects.create(
            first_name="Петр",
            last_name="Петров",
            phone="+79990000002",
            created_by=self.user,
        )
        CustomerShopHistory.objects.create(
            customer=self.other_customer,
            shop=self.other_shop,
        )

        brand = DeviceBrand.objects.create(name="Apple")
        device_type = DeviceType.objects.create(name="Смартфон")
        model = DeviceModel.objects.create(
            brand=brand,
            device_type=device_type,
            name="iPhone 15",
        )
        self.device = Device.objects.create(model=model)
        Order.objects.create(
            shop=self.other_shop,
            customer=self.other_customer,
            device=self.device,
            problem_description="Нет изображения",
            cost_estimate=5000,
            created_by=self.user,
        )

    def auth_headers(self, shop: Shop | None = None):
        payload = {
            "user_id": self.user.id,
            "username": self.user.username,
            "exp": timezone.now() + timedelta(days=1),
            "iat": timezone.now(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_CURRENT_SHOP": str((shop or self.shop).id),
        }

    def test_customer_list_is_scoped_to_current_shop(self):
        response = self.client.get(
            "/api/customers/",
            data={"page": 1, "page_size": 100},
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        names = {item["last_name"] for item in payload["items"]}
        self.assertEqual(names, {"Иванов"})

    def test_customer_detail_and_orders_reject_customer_from_another_shop(self):
        detail_response = self.client.get(
            f"/api/customers/{self.other_customer.id}",
            **self.auth_headers(),
        )
        orders_response = self.client.get(
            f"/api/customers/{self.other_customer.id}/orders",
            **self.auth_headers(),
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(orders_response.status_code, 404)
