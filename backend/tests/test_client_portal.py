import json

from django.test import Client, TestCase

from customers.models import Customer
from orders.models import Order, RepairStage
from shops.models import Shop


class ClientPortalApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.shop = Shop.objects.create(
            name="Main Repair",
            code="MAIN",
            timezone="Europe/Moscow",
            currency="RUB",
        )

    def post_json(self, path, payload, token=None):
        headers = {}
        if token:
            headers["authorization"] = f"Bearer {token}"
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            headers=headers,
        )

    def get_json(self, path, token=None):
        headers = {}
        if token:
            headers["authorization"] = f"Bearer {token}"
        return self.client.get(path, headers=headers)

    def register_customer(self, phone="+79991234567"):
        response = self.post_json(
            "/api/portal/auth/register",
            {
                "first_name": "Иван",
                "last_name": "Петров",
                "phone": phone,
                "email": "ivan@example.com",
                "password": "repair123",
                "marketing_consent": True,
            },
        )
        return response

    def test_customer_can_register_and_login_by_phone(self):
        register_response = self.register_customer()

        self.assertEqual(register_response.status_code, 201)
        payload = register_response.json()
        self.assertIn("access_token", payload)
        self.assertEqual(payload["customer"]["phone"], "+79991234567")

        login_response = self.post_json(
            "/api/portal/auth/login",
            {"phone": "+7 999 123-45-67", "password": "repair123"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access_token", login_response.json())

    def test_registration_rejects_duplicate_portal_phone(self):
        self.register_customer()
        second_response = self.register_customer()

        self.assertEqual(second_response.status_code, 400)
        self.assertEqual(
            second_response.json()["error"],
            "Клиент с таким телефоном уже зарегистрирован",
        )

    def test_login_rejects_wrong_password(self):
        self.register_customer()
        response = self.post_json(
            "/api/portal/auth/login",
            {"phone": "+79991234567", "password": "wrong1234"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Неверный телефон или пароль")

    def test_customer_can_create_repair_order_from_portal(self):
        token = self.register_customer().json()["access_token"]

        response = self.post_json(
            "/api/portal/orders",
            {
                "device_type": "Телефон",
                "brand": "Apple",
                "model_name": "iPhone 14",
                "imei": "123456789012345",
                "color": "Black",
                "storage_capacity": "128GB",
                "problem_description": "Разбит экран после падения",
                "accessories": "Коробка, кабель",
                "device_condition": "Сколы на корпусе",
                "cost_estimate": 12000,
            },
            token=token,
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["status"], Order.StatusChoices.RECEIVED)
        self.assertEqual(payload["status_display"], "Принят")
        self.assertIn("Apple iPhone 14", payload["device_title"])
        self.assertTrue(payload["order_number"].startswith("ORD-MAIN-"))
        self.assertEqual(Order.objects.count(), 1)

    def test_customer_sees_only_public_repair_stages(self):
        token = self.register_customer().json()["access_token"]
        order_payload = self.post_json(
            "/api/portal/orders",
            {
                "device_type": "Телефон",
                "brand": "Apple",
                "model_name": "iPhone 14",
                "problem_description": "Не заряжается",
                "cost_estimate": 3500,
            },
            token=token,
        ).json()
        order = Order.objects.get(id=order_payload["id"])
        RepairStage.objects.create(
            order=order,
            title="Сняли нижнюю панель",
            description="Проверили следы влаги",
            customer_visible=True,
        )
        RepairStage.objects.create(
            order=order,
            title="Внутренний контроль пайки",
            customer_visible=False,
        )

        response = self.get_json(f"/api/portal/orders/{order.id}", token=token)

        self.assertEqual(response.status_code, 200)
        stages = response.json()["repair_stages"]
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0]["title"], "Сняли нижнюю панель")

    def test_portal_order_validation_rejects_bad_imei_and_negative_price(self):
        token = self.register_customer().json()["access_token"]

        bad_imei_response = self.post_json(
            "/api/portal/orders",
            {
                "device_type": "Телефон",
                "brand": "Samsung",
                "model_name": "S24",
                "imei": "bad-imei",
                "problem_description": "Не включается после обновления",
                "cost_estimate": 0,
            },
            token=token,
        )
        negative_price_response = self.post_json(
            "/api/portal/orders",
            {
                "device_type": "Ноутбук",
                "brand": "Lenovo",
                "model_name": "ThinkPad",
                "problem_description": "Залит кофе, не работает клавиатура",
                "cost_estimate": -1,
            },
            token=token,
        )

        self.assertEqual(bad_imei_response.status_code, 400)
        self.assertEqual(
            bad_imei_response.json()["error"],
            "IMEI должен содержать только цифры",
        )
        self.assertEqual(negative_price_response.status_code, 400)
        self.assertEqual(
            negative_price_response.json()["error"],
            "Предварительная стоимость не может быть отрицательной",
        )

    def test_customer_sees_only_own_orders(self):
        first_token = self.register_customer("+79991234567").json()["access_token"]
        second_token = self.register_customer("+79997654321").json()["access_token"]

        self.post_json(
            "/api/portal/orders",
            {
                "device_type": "Телефон",
                "brand": "Apple",
                "model_name": "iPhone 13",
                "problem_description": "Не работает камера",
                "cost_estimate": 5000,
            },
            token=first_token,
        )
        self.post_json(
            "/api/portal/orders",
            {
                "device_type": "Ноутбук",
                "brand": "Asus",
                "model_name": "Zenbook",
                "problem_description": "Сильно шумит вентилятор",
                "cost_estimate": 3500,
            },
            token=second_token,
        )

        first_orders = self.get_json("/api/portal/orders", token=first_token).json()
        second_orders = self.get_json("/api/portal/orders", token=second_token).json()

        self.assertEqual(len(first_orders), 1)
        self.assertEqual(len(second_orders), 1)
        self.assertIn("iPhone 13", first_orders[0]["device_title"])
        self.assertIn("Zenbook", second_orders[0]["device_title"])

        cross_access_response = self.get_json(
            f"/api/portal/orders/{second_orders[0]['id']}",
            token=first_token,
        )

        self.assertEqual(cross_access_response.status_code, 404)
        self.assertEqual(cross_access_response.json()["error"], "Заказ не найден")

    def test_portal_orders_require_customer_token(self):
        response = self.get_json("/api/portal/orders")

        self.assertEqual(response.status_code, 401)

    def test_existing_staff_created_customer_can_activate_portal(self):
        Customer.objects.create(
            first_name="Анна",
            last_name="Смирнова",
            phone="+79990000000",
        )

        response = self.register_customer("+79990000000")

        self.assertEqual(response.status_code, 201)
        customer = Customer.objects.get(phone="+79990000000")
        self.assertTrue(customer.portal_is_active)
        self.assertTrue(customer.has_portal_password)
