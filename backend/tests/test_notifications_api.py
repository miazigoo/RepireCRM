from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notifications.models import Notification, NotificationType
from shops.models import Shop
from users.models import Role

User = get_user_model()


class NotificationsApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(
            name="Test Shop",
            code="TEST01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        self.role = Role.objects.create(name="Manager", code=Role.RoleType.MANAGER)
        self.user = User.objects.create_user(
            username="notification-user",
            password="pass12345",
            first_name="Notify",
            last_name="User",
            role=self.role,
            current_shop=self.shop,
        )
        self.user.shops.add(self.shop)
        self.notification_type = NotificationType.objects.create(
            name="Низкий остаток",
            code="low_stock",
            icon="inventory_2",
            color="#f59e0b",
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

    def test_list_notifications_serializes_type_and_visual_fields(self):
        Notification.objects.create(
            notification_type=self.notification_type,
            title="Заканчиваются чехлы",
            message="Остался 1 чехол",
            priority=Notification.Priority.HIGH,
            recipient=self.user,
            action_url="/inventory",
            data={"sku": "CASE-1"},
        )

        response = self.client.get("/api/notifications/", **self.auth_headers())

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["type"], "low_stock")
        self.assertEqual(payload[0]["icon"], "inventory_2")
        self.assertEqual(payload[0]["color"], "#f59e0b")
        self.assertFalse(payload[0]["is_read"])

    def test_list_notifications_includes_shop_and_role_notifications(self):
        Notification.objects.create(
            notification_type=self.notification_type,
            title="Склад магазина",
            message="Проверьте остатки",
            shop=self.shop,
        )
        Notification.objects.create(
            notification_type=self.notification_type,
            title="Задача менеджеру",
            message="Проверьте заказ",
            role_code=self.role.code,
        )

        response = self.client.get("/api/notifications/", **self.auth_headers())

        self.assertEqual(response.status_code, 200, response.content)
        titles = {item["title"] for item in response.json()}
        self.assertEqual(titles, {"Склад магазина", "Задача менеджеру"})

    def test_mark_read_and_mark_all_read_update_accessible_notifications(self):
        direct = Notification.objects.create(
            notification_type=self.notification_type,
            title="Личное",
            message="Тест",
            recipient=self.user,
        )
        shop_notification = Notification.objects.create(
            notification_type=self.notification_type,
            title="Магазин",
            message="Тест",
            shop=self.shop,
        )

        response = self.client.post(
            f"/api/notifications/{direct.id}/mark-read",
            **self.auth_headers(),
        )
        self.assertEqual(response.status_code, 200, response.content)
        direct.refresh_from_db()
        self.assertTrue(direct.is_read)
        self.assertIsNotNone(direct.read_at)

        response = self.client.post(
            "/api/notifications/mark-all-read",
            **self.auth_headers(),
        )
        self.assertEqual(response.status_code, 200, response.content)
        shop_notification.refresh_from_db()
        self.assertTrue(shop_notification.is_read)
