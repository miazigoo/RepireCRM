from datetime import timedelta
from decimal import Decimal

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order
from promotions.models import OrderDiscount, PromoCode, Promotion
from shops.models import Shop
from users.models import Permission, Role

User = get_user_model()


class PromotionsApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(
            name="Main Shop",
            code="MSK01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        self.role = Role.objects.create(name="Manager", code=Role.RoleType.MANAGER)
        for codename, category in (
            ("orders.view_order", Permission.PermissionCategory.ORDERS),
            ("promotions.view_promotion", Permission.PermissionCategory.MARKETING),
            ("promotions.change_promotion", Permission.PermissionCategory.MARKETING),
            ("promotions.apply_discount", Permission.PermissionCategory.MARKETING),
        ):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=category,
            )
            self.role.permissions.add(permission)
        self.user = User.objects.create_user(
            username="promo-admin",
            password="pass12345",
            first_name="Promo",
            last_name="Admin",
            role=self.role,
            current_shop=self.shop,
        )
        self.user.shops.add(self.shop)
        self.customer = Customer.objects.create(
            first_name="Иван",
            last_name="Петров",
            phone="+79001112233",
            email="ivan@example.com",
        )
        device_type = DeviceType.objects.create(name="Смартфон")
        brand = DeviceBrand.objects.create(name="Apple")
        model = DeviceModel.objects.create(
            brand=brand,
            device_type=device_type,
            name="iPhone 15",
        )
        device = Device.objects.create(model=model, color="Черный")
        self.order = Order.objects.create(
            shop=self.shop,
            customer=self.customer,
            device=device,
            problem_description="Не заряжается",
            cost_estimate=Decimal("10000.00"),
            prepayment=Decimal("1000.00"),
            created_by=self.user,
        )
        self.promotion = Promotion.objects.create(
            name="Стартовая скидка",
            discount_type=Promotion.DiscountType.PERCENT,
            value=Decimal("10.00"),
            min_order_amount=Decimal("1000.00"),
            is_active=True,
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=30),
            created_by=self.user,
        )
        self.promotion.shops.add(self.shop)
        self.promo_code = PromoCode.objects.create(
            promotion=self.promotion,
            code="START10",
            is_active=True,
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

    def test_validate_promo_code_for_order(self):
        response = self.client.post(
            "/api/promotions/validate-code",
            data={"code": "start10", "order_id": self.order.id},
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["discount_amount"], 1000.0)
        self.assertEqual(payload["total_after_discount"], 9000.0)

    def test_apply_and_remove_promo_code_updates_order_totals(self):
        response = self.client.post(
            f"/api/promotions/orders/{self.order.id}/apply-code",
            data={"code": "START10"},
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        discount = OrderDiscount.objects.get(
            order=self.order, promo_code=self.promo_code
        )
        self.assertEqual(discount.amount, Decimal("1000.00"))

        order_response = self.client.get(
            f"/api/orders/{self.order.id}",
            **self.auth_headers(),
        )
        self.assertEqual(order_response.status_code, 200, order_response.content)
        order_payload = order_response.json()
        self.assertEqual(order_payload["discount_total"], 1000.0)
        self.assertEqual(order_payload["total_cost"], 9000.0)
        self.assertEqual(order_payload["remaining_payment"], 8000.0)
        self.assertEqual(order_payload["discounts"][0]["promo_code"], "START10")

        delete_response = self.client.delete(
            f"/api/promotions/orders/{self.order.id}/discounts/{discount.id}",
            **self.auth_headers(),
        )
        self.assertEqual(delete_response.status_code, 200, delete_response.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.discount_total, Decimal("0.00"))
        self.assertEqual(self.order.total_cost, Decimal("10000.00"))

    def test_legacy_portal_api_is_removed(self):
        response = self.client.get("/api/portal/orders", **self.auth_headers())

        self.assertEqual(response.status_code, 404)
