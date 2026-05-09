import json
from datetime import timedelta

import jwt
import requests
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
    push_marketing_snapshot,
    push_order_snapshots,
    serialize_order_snapshot,
)
from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from finance.models import Payment, PaymentMethod
from orders.models import Order, OrderApproval, RepairStage
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


class FailingPostSession:
    def post(self, url, **kwargs):
        raise requests.Timeout("client portal timeout")


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
        order_posts = [p for p in session.posts if "orders/upsert" in p["url"]]
        self.assertEqual(len(order_posts), 1)
        self.assertEqual(
            order_posts[0]["headers"]["X-Sync-Token"],
            "sync-secret",
        )
        self.assertEqual(
            order_posts[0]["json"]["orders"][0]["order_number"],
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

    def test_child_order_change_marks_synced_order_pending(self):
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
        push_order_snapshots(self.integration, session=session)
        state = ClientSyncOrderState.objects.get(order=self.order)
        self.assertEqual(state.status, ClientSyncOrderState.Status.SYNCED)

        with self.captureOnCommitCallbacks(execute=True):
            RepairStage.objects.create(
                order=self.order,
                title="Фото до ремонта",
                description="Клиенту видно",
                created_by=self.user,
            )

        state.refresh_from_db()
        self.assertEqual(state.status, ClientSyncOrderState.Status.PENDING)

    def test_payment_change_is_pushed_even_when_order_timestamp_is_unchanged(self):
        first_session = FakeSession(
            post_payload={
                "orders": [
                    {
                        "crm_order_id": self.order.id,
                        "remote_order_id": "remote-123",
                    }
                ]
            }
        )
        push_order_snapshots(self.integration, session=first_session)
        state = ClientSyncOrderState.objects.get(order=self.order)
        self.assertEqual(state.status, ClientSyncOrderState.Status.SYNCED)

        method = PaymentMethod.objects.create(name="Наличные", code="cash")
        with self.captureOnCommitCallbacks(execute=True):
            Payment.objects.create(
                payment_type=Payment.PaymentType.INCOME,
                status=Payment.PaymentStatus.COMPLETED,
                amount=1000,
                payment_method=method,
                order=self.order,
                created_by=self.user,
                payment_date=timezone.now(),
            )

        state.refresh_from_db()
        self.assertEqual(state.status, ClientSyncOrderState.Status.PENDING)

        second_session = FakeSession(
            post_payload={
                "orders": [
                    {
                        "crm_order_id": self.order.id,
                        "remote_order_id": "remote-123",
                    }
                ]
            }
        )
        result = push_order_snapshots(self.integration, session=second_session)

        self.assertEqual(result.pushed, 1)
        order_payload = second_session.posts[0]["json"]["orders"][0]
        self.assertEqual(order_payload["payments"][0]["amount"], "1000.00")
        self.assertEqual(order_payload["payments"][0]["payment_method"], "Наличные")

    def test_push_network_error_marks_order_state_error(self):
        result = push_order_snapshots(self.integration, session=FailingPostSession())

        self.assertEqual(result.errors, 1)
        state = ClientSyncOrderState.objects.get(order=self.order)
        self.assertEqual(state.status, ClientSyncOrderState.Status.ERROR)
        self.assertIn("timeout", state.last_error)
        self.integration.refresh_from_db()
        self.assertIn("timeout", self.integration.last_error)

    def test_pull_rejects_approval_from_other_organization(self):
        other_org = Organization.objects.create(name="Other Org")
        other_shop = Shop.objects.create(name="Other Shop", code="SPB01")
        ShopSettings.objects.create(shop=other_shop, organization=other_org)
        other_order = Order.objects.create(
            shop=other_shop,
            customer=self.customer,
            device=self.device,
            problem_description="Другая организация",
            cost_estimate=1000,
            created_by=self.user,
        )
        approval = OrderApproval.objects.create(
            order=other_order,
            title="Чужое согласование",
            amount=1000,
            requested_by=self.user,
        )
        session = FakeSession(
            get_payload={
                "actions": [
                    {
                        "id": "act-foreign",
                        "type": "approval.decided",
                        "payload": {
                            "crm_approval_id": approval.id,
                            "status": "approved",
                        },
                    }
                ]
            }
        )

        result = pull_pending_actions(self.integration, session=session)

        self.assertEqual(result.pulled, 1)
        self.assertEqual(result.errors, 1)
        approval.refresh_from_db()
        self.assertEqual(approval.status, OrderApproval.StatusChoices.PENDING)
        action = ClientSyncAction.objects.get(external_id="act-foreign")
        self.assertEqual(action.status, ClientSyncAction.Status.ERROR)
        self.assertIn("does not belong", action.error_message)

    def test_portal_repair_request_mark_synced_contains_crm_order_number(self):
        session = FakeSession(
            get_payload={
                "actions": [
                    {
                        "id": "act-request",
                        "type": "repair_request.created",
                        "payload": {
                            "client_order_id": 55,
                            "customer": {
                                "first_name": self.customer.first_name,
                                "last_name": self.customer.last_name,
                                "phone": str(self.customer.phone),
                                "email": self.customer.email,
                            },
                            "device": {
                                "device_type": "Смартфон",
                                "brand": "Apple",
                                "model_name": "iPhone 15",
                            },
                            "order": {
                                "problem_description": "Разбит экран после падения",
                                "cost_estimate": 0,
                            },
                        },
                    }
                ]
            }
        )

        result = pull_pending_actions(self.integration, session=session)

        self.assertEqual(result.applied, 1)
        action = ClientSyncAction.objects.get(external_id="act-request")
        self.assertIsNotNone(action.related_order_id)
        mark_posts = [p for p in session.posts if "mark-synced" in p["url"]]
        self.assertEqual(len(mark_posts), 1)
        self.assertEqual(mark_posts[0]["json"]["crm_order_id"], action.related_order_id)
        self.assertEqual(
            mark_posts[0]["json"]["crm_order_number"],
            action.related_order.order_number,
        )

    def test_portal_repair_request_is_idempotent_by_external_action_id(self):
        existing = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=self.device,
            problem_description="Повторная заявка",
            cost_estimate=0,
            created_by=self.user,
            notes="Заявка клиента из внешнего кабинета. Action: act-request-repeat",
        )
        session = FakeSession(
            get_payload={
                "actions": [
                    {
                        "id": "act-request-repeat",
                        "type": "repair_request.created",
                        "payload": {
                            "client_order_id": 77,
                            "customer": {
                                "first_name": self.customer.first_name,
                                "last_name": self.customer.last_name,
                                "phone": str(self.customer.phone),
                                "email": self.customer.email,
                            },
                            "device": {
                                "device_type": "Смартфон",
                                "brand": "Apple",
                                "model_name": "iPhone 15",
                            },
                            "order": {
                                "problem_description": "Повторная заявка",
                                "cost_estimate": 0,
                            },
                        },
                    }
                ]
            }
        )

        result = pull_pending_actions(self.integration, session=session)

        self.assertEqual(result.applied, 1)
        action = ClientSyncAction.objects.get(external_id="act-request-repeat")
        self.assertEqual(action.related_order_id, existing.id)
        self.assertEqual(
            Order.objects.filter(
                notes__contains="Action: act-request-repeat",
            ).count(),
            1,
        )

    def test_push_marketing_snapshot_posts_payload(self):
        session = FakeSession()
        ok = push_marketing_snapshot(self.integration, session=session)
        self.assertTrue(ok)
        self.assertEqual(len(session.posts), 1)
        self.assertTrue(session.posts[0]["url"].endswith("/api/sync/marketing/upsert"))
        payload = session.posts[0]["json"]
        self.assertEqual(payload["tenant_key"], "test-company")
        self.assertIn("promotions", payload)
        self.assertIn("banner", payload)
