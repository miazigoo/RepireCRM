from datetime import datetime, time, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from shops.models import Shop
from tasks.models import Task, TaskCategory, TaskTemplate
from users.models import Permission, Role

User = get_user_model()


class TasksApiTestCase(TestCase):
    def setUp(self):
        self.shop = Shop.objects.create(
            name="Test Shop",
            code="TEST01",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        self.role = Role.objects.create(name="Manager", code=Role.RoleType.MANAGER)
        for codename in ("tasks.view_task", "tasks.view_template"):
            permission = Permission.objects.create(
                name=codename,
                codename=codename,
                category=Permission.PermissionCategory.SETTINGS,
            )
            self.role.permissions.add(permission)

        self.user = User.objects.create_user(
            username="tasks-user",
            password="pass12345",
            first_name="Tasks",
            last_name="User",
            role=self.role,
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

    def test_my_tasks_summary_static_route_returns_summary(self):
        Task.objects.create(
            title="Проверить заказ",
            description="Контрольная задача",
            status=Task.Status.IN_PROGRESS,
            assignment_type=Task.AssignmentType.INDIVIDUAL,
            assigned_to=self.user,
            created_by=self.user,
            due_date=timezone.make_aware(
                datetime.combine(timezone.now().date(), time(hour=12)),
                timezone.get_current_timezone(),
            ),
        )

        response = self.client.get(
            "/api/tasks/my-tasks-summary",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["total_tasks"], 1)
        self.assertEqual(payload["due_today"], 1)

    def test_templates_static_route_returns_templates(self):
        category = TaskCategory.objects.create(name="Сервис")
        TaskTemplate.objects.create(
            name="Первичная диагностика",
            title_template="Диагностика {order}",
            description_template="Проверить устройство",
            category=category,
            created_by=self.user,
        )

        response = self.client.get(
            "/api/tasks/templates",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload[0]["name"], "Первичная диагностика")
        self.assertEqual(payload[0]["category"], "Сервис")
