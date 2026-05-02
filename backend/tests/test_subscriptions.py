import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notifications.models import Notification
from shops.models import (
    Organization,
    OrganizationSubscription,
    Shop,
    ShopSettings,
    SubscriptionPlan,
)
from shops.subscription_services import (
    change_subscription_plan,
    ensure_default_subscription_plans,
    notify_subscription_if_needed,
    refresh_subscription_status,
)
from users.models import Permission, Role

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

    def create_user_without_settings_permissions(self):
        role = Role.objects.create(name="Техник", code=Role.RoleType.TECHNICIAN)
        user = User.objects.create_user(
            username="tech",
            password="pass12345",
            first_name="Tech",
            last_name="User",
            role=role,
            current_shop=self.shop,
        )
        user.shops.add(self.shop)
        return user

    def create_settings_admin(self, username="settings-admin"):
        role = Role.objects.create(name=f"Admin {username}", code=Role.RoleType.ADMIN)
        for codename in ("settings.view_shop", "settings.change_shop"):
            permission, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    "name": codename,
                    "category": Permission.PermissionCategory.SETTINGS,
                },
            )
            role.permissions.add(permission)
        user = User.objects.create_user(
            username=username,
            password="pass12345",
            first_name="Admin",
            last_name="User",
            role=role,
            current_shop=self.shop,
        )
        user.shops.add(self.shop)
        return user

    def auth_headers(self, user=None, shop=None):
        user = user or self.user
        shop = shop or self.shop
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
        self.assertEqual(payload["color_hex"], "#1b8f3a")

    def test_subscription_plans_include_trial_and_paid_periods(self):
        response = self.client.get(
            "/api/shops/subscription/plans",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        plans = {plan["code"]: plan for plan in response.json()}
        self.assertEqual(set(plans), {"trial", "monthly", "half_year", "yearly"})
        self.assertEqual(plans["trial"]["duration_days"], 45)
        self.assertEqual(plans["monthly"]["price"], 1490.0)
        self.assertEqual(plans["half_year"]["duration_days"], 182)
        self.assertEqual(plans["yearly"]["duration_days"], 365)

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

    def test_settings_admin_can_manage_subscription_without_superuser_flag(self):
        admin = self.create_settings_admin()

        response = self.client.post(
            "/api/shops/subscription/change",
            data=json.dumps({"plan_code": "monthly"}),
            content_type="application/json",
            **self.auth_headers(user=admin),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["plan"]["code"], "monthly")

    def test_subscription_change_rejects_unknown_plan(self):
        response = self.client.post(
            "/api/shops/subscription/change",
            data=json.dumps({"plan_code": "enterprise-plus"}),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Тариф подписки не найден")

    def test_subscription_status_requires_settings_permission(self):
        user = self.create_user_without_settings_permissions()

        response = self.client.get(
            "/api/shops/subscription/status",
            **self.auth_headers(user=user),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "Нет прав")

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

    def test_subscription_color_bucket_rounds_down_by_ten_percent_steps(self):
        subscription = change_subscription_plan(self.organization, "monthly")
        now = timezone.now()
        subscription.started_at = now - timedelta(days=22)
        subscription.expires_at = now + timedelta(days=8)
        subscription.save(update_fields=["started_at", "expires_at"])

        response = self.client.get(
            "/api/shops/subscription/status",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["remaining_percent"], 27)
        self.assertEqual(payload["color_bucket"], 20)
        self.assertEqual(payload["color_hex"], "#e95f34")

    def test_expired_subscription_is_marked_expired(self):
        ensure_default_subscription_plans()
        plan = SubscriptionPlan.objects.get(code="monthly")
        now = timezone.now()
        subscription = OrganizationSubscription.objects.create(
            organization=self.organization,
            plan=plan,
            status=OrganizationSubscription.Status.ACTIVE,
            started_at=now - timedelta(days=31),
            expires_at=now - timedelta(days=1),
        )

        refresh_subscription_status(subscription)

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, OrganizationSubscription.Status.EXPIRED)
        self.assertEqual(subscription.remaining_days, 0)
        self.assertEqual(subscription.color_bucket, 0)

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

    def test_subscription_notice_is_not_sent_before_notice_bucket(self):
        subscription = change_subscription_plan(self.organization, "monthly")
        now = timezone.now()
        subscription.started_at = now - timedelta(days=15)
        subscription.expires_at = now + timedelta(days=15)
        subscription.save(update_fields=["started_at", "expires_at"])

        sent = notify_subscription_if_needed(subscription)

        self.assertFalse(sent)
        self.assertEqual(Notification.objects.count(), 0)
