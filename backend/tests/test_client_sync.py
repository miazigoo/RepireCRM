import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from client_sync.models import (
    ClientPortalIntegration,
    ClientSyncAction,
    ClientSyncOrderState,
)
from client_sync.services import (
    pull_pending_actions,
    push_order_snapshots,
    serialize_order_snapshot,
)
from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order, OrderApproval
from shops.models import Organization, Shop, ShopSettings
from users.models import Permission, Role

User = get_user_model()


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text="OK"):
        self.payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, get_payload=None, post_payload=None):
        self.get_payload = get_payload if get_payload is not None else {"actions": []}
        self.post_payload = post_payload if post_payload is not None else {"orders": []}
        self.posts = []
        self.gets = []

    def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        if url.endswith("/mark-synced"):
            return FakeResponse({})
        return FakeResponse(self.post_payload)

    def get(self, url, **kwargs):
        self.gets.append({"url": url, **kwargs})
        return FakeResponse(self.get_payload)


class ClientSyncTestCase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Repair CRM Test",
            phone="+79990000000",
            email="support@example.com",
        )
        self.shop = Shop.objects.create(
            name="Main Shop",
            code="MSK01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        ShopSettings.objects.create(shop=self.shop, organization=self.organization)
        self.role = Role.objects.create(name="Admin", code=Role.RoleType.ADMIN)
        for codename in ("settings.view_shop", "settings.change_shop"):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=Permission.PermissionCategory.SETTINGS,
            )
            self.role.permissions.add(permission)
        self.user = User.objects.create_user(
            username="sync-admin",
            password="pass12345",
            first_name="Sync",
            last_name="Admin",
            role=self.role,
            current_shop=self.shop,
        )
        self.user.shops.add(self.shop)
        self.customer = Customer.objects.create(
            first_name="Иван",
            last_name="Петров",
            phone="+79001111111",
            email="ivan@example.com",
        )
        device_type = DeviceType.objects.create(name="Смартфон")
        brand = DeviceBrand.objects.create(name="Apple")
        model = DeviceModel.objects.create(
            brand=brand,
            device_type=device_type,
            name="iPhone 14",
        )
        self.device = Device.objects.create(
            model=model,
            imei="123456789012345",
            color="Черный",
        )
        self.order = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=self.device,
            problem_description="Не включается",
            cost_estimate=5000,
            created_by=self.user,
            estimated_completion=timezone.now() + timedelta(days=2),
        )
        self.integration = ClientPortalIntegration.objects.create(
            organization=self.organization,
            enabled=True,
            base_url="https://client.example.com",
            api_key="sync-secret",
            tenant_key="test-company",
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

    def test_status_endpoint_is_optional_and_masks_api_key(self):
        response = self.client.get("/api/client-sync/status", **self.auth_headers())

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()["integration"]
        self.assertTrue(payload["configured"])
        self.assertTrue(payload["api_key_configured"])
        self.assertNotIn("sync-secret", json.dumps(payload))

    def test_order_snapshot_contains_customer_device_warranty_and_decimal_money(self):
        snapshot = serialize_order_snapshot(self.order)

        self.assertEqual(snapshot["crm_order_id"], self.order.id)
        self.assertEqual(snapshot["customer"]["phone"], "+79001111111")
        self.assertEqual(snapshot["device"]["brand"], "Apple")
        self.assertEqual(snapshot["cost_estimate"], "5000")
        self.assertEqual(snapshot["warranty_days"], 90)

    def test_push_order_snapshots_upserts_changed_orders(self):
        session = FakeSession(
            post_payload={
                "orders": [
                    {
                        "crm_order_id": self.order.id,
                        "remote_order_id": "remote-123",
                    }
                ]
            }
        )

        result = push_order_snapshots(self.integration, session=session)

        self.assertEqual(result.pushed, 1)
        self.assertEqual(len(session.posts), 1)
        self.assertEqual(
            session.posts[0]["headers"]["X-Sync-Token"],
            "sync-secret",
        )
        self.assertEqual(
            session.posts[0]["json"]["orders"][0]["order_number"],
            self.order.order_number,
        )
        state = ClientSyncOrderState.objects.get(order=self.order)
        self.assertEqual(state.status, ClientSyncOrderState.Status.SYNCED)
        self.assertEqual(state.remote_order_id, "remote-123")

    def test_pull_pending_approval_action_applies_and_marks_remote(self):
        approval = OrderApproval.objects.create(
            order=self.order,
            title="Согласование ремонта",
            description="Замена дисплея",
            amount=6500,
            requested_by=self.user,
        )
        session = FakeSession(
            get_payload={
                "actions": [
                    {
                        "id": "act-1",
                        "type": "approval.decided",
                        "payload": {
                            "crm_approval_id": approval.id,
                            "status": "approved",
                            "comment": "Согласен",
                        },
                    }
                ]
            }
        )

        result = pull_pending_actions(self.integration, session=session)

        self.assertEqual(result.pulled, 1)
        self.assertEqual(result.applied, 1)
        approval.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(approval.status, OrderApproval.StatusChoices.APPROVED)
        self.assertEqual(approval.customer_comment, "Согласен")
        self.assertEqual(self.order.cost_estimate, approval.amount)
        action = ClientSyncAction.objects.get(external_id="act-1")
        self.assertEqual(action.status, ClientSyncAction.Status.APPLIED)
        self.assertIsNotNone(action.synced_back_at)
        self.assertTrue(
            session.posts[0]["url"].endswith("/api/sync/actions/act-1/mark-synced")
        )
