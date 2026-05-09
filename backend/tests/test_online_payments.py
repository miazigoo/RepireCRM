import json
from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from finance.models import OnlinePayment, Payment
from orders.models import Order
from shops.models import Organization, OrganizationSubscription, Shop, ShopSettings
from users.models import Permission, Role

User = get_user_model()


@override_settings(
    YOOKASSA_MOCK=True,
    FRONTEND_URL="http://front.test",
    BACKEND_PUBLIC_URL="http://backend.test",
)
class OnlinePaymentApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Main", code="MAIN")
        self.organization = Organization.objects.create(name="Main Org")
        ShopSettings.objects.create(shop=self.shop, organization=self.organization)
        self.role = Role.objects.create(name="Director", code=Role.RoleType.DIRECTOR)
        for codename, category in (
            ("finance.add_payment", Permission.PermissionCategory.FINANCE),
            ("settings.view_shop", Permission.PermissionCategory.SETTINGS),
            ("settings.change_shop", Permission.PermissionCategory.SETTINGS),
        ):
            permission, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={"name": codename, "category": category},
            )
            self.role.permissions.add(permission)

        self.user = User.objects.create_user(
            username="owner",
            password="pass12345",
            first_name="Owner",
            last_name="User",
            role=self.role,
            current_shop=self.shop,
            is_director=True,
        )
        self.user.shops.add(self.shop)

        customer = Customer.objects.create(
            first_name="Ivan",
            last_name="Ivanov",
            phone="+79991234567",
        )
        brand = DeviceBrand.objects.create(name="Apple")
        device_type = DeviceType.objects.create(name="Смартфон")
        model = DeviceModel.objects.create(
            brand=brand,
            device_type=device_type,
            name="iPhone 15",
        )
        device = Device.objects.create(model=model)
        self.order = Order.objects.create(
            shop=self.shop,
            customer=customer,
            device=device,
            problem_description="Не включается",
            cost_estimate=5000,
            prepayment=1000,
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

    def test_order_online_payment_mock_checkout_marks_order_paid(self):
        response = self.client.post(
            f"/api/finance/order/{self.order.id}/online-payment",
            data=json.dumps({"payment_method_type": "sbp"}),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["payment_method_type"], "sbp")
        self.assertEqual(payload["amount"], 4000.0)
        self.assertIn("/test-checkout", payload["confirmation_url"])

        payment = OnlinePayment.objects.get(id=payload["id"])
        confirm_url = (
            f"/api/finance/online-payments/{payment.id}/test-confirm"
            f"?token={payment.test_token}"
        )
        confirm_response = self.client.post(
            confirm_url,
        )

        self.assertEqual(confirm_response.status_code, 302, confirm_response.content)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, OnlinePayment.Status.SUCCEEDED)
        self.assertEqual(self.order.prepayment, 5000)
        self.assertTrue(Payment.objects.filter(order=self.order).exists())

    def test_subscription_online_payment_activates_plan_after_success(self):
        response = self.client.post(
            "/api/shops/subscription/pay",
            data=json.dumps(
                {"plan_code": "monthly", "payment_method_type": "bank_card"}
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payment = OnlinePayment.objects.get(id=response.json()["id"])
        self.assertEqual(payment.purpose, OnlinePayment.Purpose.SUBSCRIPTION)

        confirm_url = (
            f"/api/finance/online-payments/{payment.id}/test-confirm"
            f"?token={payment.test_token}"
        )
        confirm_response = self.client.post(
            confirm_url,
        )

        self.assertEqual(confirm_response.status_code, 302, confirm_response.content)
        subscription = OrganizationSubscription.objects.get(
            organization=self.organization
        )
        self.assertEqual(subscription.plan.code, "monthly")
        self.assertEqual(subscription.status, OrganizationSubscription.Status.ACTIVE)
