import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notifications.models import Notification
from shops.models import Organization, Shop, ShopSettings
from shops.subscription_services import (
    change_subscription_plan,
    notify_subscription_if_needed,
)
from users.models import Role

User = get_user_model()


class SubscriptionApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Main", code="MAIN")
        self.organization = Organization.objects.create(name="Main Org")
        ShopSettings.objects.create(shop=self.shop, organization=self.organization)
        self.user = User.objects.create_user(
            username="owner",
            password="pass12345",
            first_name="Owner",
            last_name="User",
            is_superuser=True,
            is_director=True,
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

    def test_subscription_status_creates_45_day_trial(self):
        response = self.client.get(
            "/api/shops/subscription/status",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["status"], "trial")
        self.assertEqual(payload["plan"]["code"], "trial")
        self.assertEqual(payload["remaining_days"], 45)
        self.assertEqual(payload["remaining_percent"], 100)
        self.assertEqual(payload["color_bucket"], 100)

    def test_subscription_can_change_to_yearly_plan(self):
        response = self.client.post(
            "/api/shops/subscription/change",
            data=json.dumps({"plan_code": "yearly"}),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["plan"]["code"], "yearly")
        self.assertGreaterEqual(payload["remaining_days"], 364)

    def test_subscription_color_buckets_are_based_on_remaining_percent(self):
        subscription = change_subscription_plan(self.organization, "yearly")
        now = timezone.now()
        subscription.started_at = now - timedelta(days=183)
        subscription.expires_at = now + timedelta(days=182)
        subscription.save(update_fields=["started_at", "expires_at"])

        response = self.client.get(
            "/api/shops/subscription/status",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["color_bucket"], 50)
        self.assertTrue(payload["color_hex"].startswith("#"))

    def test_subscription_ending_notifies_owner_and_admin_once_per_bucket(self):
        admin_role = Role.objects.create(
            name="Администратор",
            code=Role.RoleType.ADMIN,
        )
        admin = User.objects.create_user(
            username="admin",
            password="pass12345",
            first_name="Admin",
            last_name="User",
            role=admin_role,
            current_shop=self.shop,
        )
        admin.shops.add(self.shop)
        subscription = change_subscription_plan(self.organization, "monthly")
        now = timezone.now()
        subscription.started_at = now - timedelta(days=27)
        subscription.expires_at = now + timedelta(days=3)
        subscription.save(update_fields=["started_at", "expires_at"])

        first_sent = notify_subscription_if_needed(subscription)
        second_sent = notify_subscription_if_needed(subscription)

        self.assertTrue(first_sent)
        self.assertFalse(second_sent)
        self.assertEqual(Notification.objects.count(), 2)
        recipients = set(Notification.objects.values_list("recipient_id", flat=True))
        self.assertEqual(recipients, {self.user.id, admin.id})
        self.assertTrue(Notification.objects.filter(data__color_bucket=10).exists())
