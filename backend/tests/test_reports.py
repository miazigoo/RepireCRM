from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from shops.models import Shop
from users.models import Permission, Role

User = get_user_model()


class ReportsApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(
            name="Test Shop",
            code="TEST01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        role = Role.objects.create(name="Director", code=Role.RoleType.DIRECTOR)
        for codename in (
            "reports.view_dashboard",
            "reports.view_financial",
            "reports.export_reports",
        ):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=Permission.PermissionCategory.REPORTS,
            )
            role.permissions.add(permission)
        self.user = User.objects.create_user(
            username="reports-user",
            password="pass12345",
            first_name="Reports",
            last_name="User",
            role=role,
            current_shop=self.shop,
            is_director=True,
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

    def test_dashboard_metrics_returns_empty_metrics_without_order_services(self):
        response = self.client.get(
            "/api/reports/dashboard-metrics",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["orders"]["total"], 0)
        self.assertEqual(payload["top_services"], [])
        self.assertEqual(payload["technician_performance"], [])

    def test_financial_report_returns_empty_breakdowns_without_order_services(self):
        now = timezone.now()
        response = self.client.get(
            "/api/reports/financial",
            data={
                "date_from": (now - timedelta(days=30)).isoformat(),
                "date_to": now.isoformat(),
            },
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["summary"]["total_orders"], 0)
        self.assertEqual(payload["services_breakdown"], [])

    def test_dashboard_export_static_route_is_not_treated_as_report_id(self):
        response = self.client.get(
            "/api/reports/export/dashboard",
            data={"period": "30_days", "format": "pdf"},
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response["Content-Type"], "application/pdf")
