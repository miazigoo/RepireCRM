import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order
from shops.models import Shop

User = get_user_model()


class OrderTestCase(TestCase):
    def setUp(self):
        # Создаем тестовые данные
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        self.shop = Shop.objects.create(
            name="Test Shop", code="TEST01", timezone="Europe/Moscow", currency="RUB"
        )

        self.customer = Customer.objects.create(
            first_name="John", last_name="Doe", phone="+79991234567"
        )

        # Создаем устройство
        brand = DeviceBrand.objects.create(name="Apple")
        device_type = DeviceType.objects.create(name="iPhone")
        model = DeviceModel.objects.create(
            brand=brand, device_type=device_type, name="iPhone 12"
        )

        self.device = Device.objects.create(
            model=model, color="Black", storage_capacity="128GB"
        )

    def test_create_order(self):
        """Тест создания заказа"""
        order = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=self.device,
            problem_description="Экран не работает",
            cost_estimate=5000.00,
            created_by=self.user,
        )

        self.assertEqual(order.status, Order.StatusChoices.RECEIVED)
        self.assertEqual(order.priority, Order.PriorityChoices.NORMAL)
        self.assertTrue(order.order_number.startswith("ORD-TEST01-"))

    def test_order_total_cost_calculation(self):
        """Тест расчета общей стоимости"""
        order = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=self.device,
            problem_description="Test",
            cost_estimate=5000.00,
            prepayment=1000.00,
            created_by=self.user,
        )

        self.assertEqual(order.total_cost, 5000.00)
        self.assertEqual(order.remaining_payment, 4000.00)
