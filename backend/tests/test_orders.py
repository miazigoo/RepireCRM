import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import (
    Order,
    OrderApproval,
    OrderAuditLog,
    OrderStatusHistory,
    RepairStage,
)
from shops.models import Shop
from users.models import Permission, Role

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
        self.user.current_shop = self.shop
        self.user.is_superuser = True
        role = Role.objects.create(name="Manager", code=Role.RoleType.MANAGER)
        for codename in (
            "orders.view_order",
            "orders.add_order",
            "orders.change_order",
            "orders.change_status",
        ):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=Permission.PermissionCategory.ORDERS,
            )
            role.permissions.add(permission)
        self.user.role = role
        self.user.save(update_fields=["current_shop", "is_superuser", "role"])
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

    def auth_headers_mapping(self):
        headers = self.auth_headers()
        return {
            "authorization": headers["HTTP_AUTHORIZATION"],
            "x-current-shop": headers["HTTP_X_CURRENT_SHOP"],
        }

    def create_order(self):
        return Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=self.device,
            problem_description="Экран не работает",
            cost_estimate=5000.00,
            created_by=self.user,
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

    def test_status_change_api_creates_history_and_audit_log(self):
        order = self.create_order()

        response = self.client.put(
            f"/api/orders/{order.id}",
            data=json.dumps(
                {
                    "status": Order.StatusChoices.DIAGNOSED,
                    "diagnosis": "Нужна замена дисплея",
                    "status_comment": "Диагностика завершена",
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.StatusChoices.DIAGNOSED)
        history = OrderStatusHistory.objects.get(order=order)
        self.assertEqual(history.old_status, Order.StatusChoices.RECEIVED)
        self.assertEqual(history.new_status, Order.StatusChoices.DIAGNOSED)
        self.assertEqual(history.comment, "Диагностика завершена")
        self.assertTrue(
            OrderAuditLog.objects.filter(
                order=order,
                action=OrderAuditLog.ActionChoices.STATUS_CHANGED,
            ).exists()
        )

        history_response = self.client.get(
            f"/api/orders/{order.id}/status-history",
            **self.auth_headers(),
        )

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()[0]["new_status"], "diagnosed")

    def test_order_statistics_static_route_is_not_treated_as_order_id(self):
        order = self.create_order()
        order.final_cost = 5000
        order.save(update_fields=["final_cost"])

        response = self.client.get(
            "/api/orders/statistics",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["total_orders"], 1)
        self.assertEqual(payload["total_revenue"], 5000.0)

    def test_order_catalog_static_routes_are_not_treated_as_order_id(self):
        static_routes = (
            "/api/orders/additional-services",
            "/api/orders/device-models",
            "/api/orders/repair-services",
        )

        for route in static_routes:
            with self.subTest(route=route):
                response = self.client.get(route, **self.auth_headers())

                self.assertEqual(response.status_code, 200, response.content)

    def test_create_order_endpoint_accepts_trailing_slash_post(self):
        response = self.client.post(
            "/api/orders/",
            data=json.dumps(
                {
                    "customer_id": self.customer.id,
                    "device": {
                        "model_id": self.device.model_id,
                        "serial_number": "",
                        "imei": "",
                        "color": "Black",
                        "storage_capacity": "128GB",
                    },
                    "problem_description": "Не заряжается",
                    "cost_estimate": 1500,
                    "priority": "normal",
                    "additional_services": [],
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn("order_number", response.json())

    def test_staff_can_create_missing_device_model_from_order_form(self):
        response = self.client.post(
            "/api/orders/device-models",
            data=json.dumps(
                {
                    "brand_name": "Samsung",
                    "name": "Galaxy A55",
                    "device_type_name": "Смартфон",
                    "model_number": "SM-A556E",
                    "release_year": 2024,
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertEqual(payload["brand"]["name"], "Samsung")
        self.assertEqual(payload["name"], "Galaxy A55")

    @override_settings(MEDIA_ROOT="/tmp/repair_crm_test_media")
    def test_repair_stage_api_accepts_photo_and_writes_audit_log(self):
        order = self.create_order()
        photo = SimpleUploadedFile(
            "typec-before.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )

        response = self.client.post(
            f"/api/orders/{order.id}/repair-stages",
            data={
                "title": "Перепаяли Type-C",
                "description": "Старый разъем был поврежден",
                "customer_visible": "true",
                "photo": photo,
            },
            headers=self.auth_headers_mapping(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        stage = RepairStage.objects.get(order=order)
        self.assertEqual(stage.title, "Перепаяли Type-C")
        self.assertTrue(stage.customer_visible)
        self.assertTrue(stage.photo.name.startswith("repair_stages/"))
        self.assertTrue(
            OrderAuditLog.objects.filter(
                order=order,
                action=OrderAuditLog.ActionChoices.STAGE_ADDED,
            ).exists()
        )

    def test_staff_can_request_customer_approval(self):
        order = self.create_order()

        response = self.client.post(
            f"/api/orders/{order.id}/approvals",
            data=json.dumps(
                {
                    "title": "Согласование замены Type-C",
                    "description": "Нужно заменить разъем и проверить питание",
                    "amount": 4500,
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        approval = OrderApproval.objects.get(order=order)
        self.assertEqual(approval.status, OrderApproval.StatusChoices.PENDING)
        self.assertEqual(approval.amount, 4500)
        self.assertTrue(
            OrderAuditLog.objects.filter(
                order=order,
                action=OrderAuditLog.ActionChoices.APPROVAL_REQUESTED,
            ).exists()
        )
