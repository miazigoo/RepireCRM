import json
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
        for codename in (
            "tasks.view_task",
            "tasks.view_template",
            "tasks.add_task",
        ):
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

    def test_create_task_defaults_nullable_attachments_to_list(self):
        response = self.client.post(
            "/api/tasks/",
            data=json.dumps(
                {
                    "title": "Проверить витрину",
                    "description": "Проверка после смены",
                    "assignment_type": "individual",
                    "assigned_to_id": self.user.id,
                    "priority": "normal",
                    "kind": "regular",
                    "substatus": "new",
                    "status": "pending",
                    "is_paid": True,
                    "payment_amount": 550,
                    "attachments": None,
                }
            ),
            content_type="application/json",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        task = Task.objects.get(id=response.json()["id"])
        self.assertEqual(task.attachments, [])
        self.assertEqual(task.payment_amount, 550)

    def test_director_sees_created_task_assigned_outside_current_shop(self):
        second_shop = Shop.objects.create(
            name="Second Shop",
            code="TEST02",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        assignee = User.objects.create_user(
            username="second-shop-worker",
            password="pass12345",
            first_name="Second",
            last_name="Worker",
            role=self.role,
            current_shop=second_shop,
        )
        assignee.shops.add(second_shop)
        task = Task.objects.create(
            title="Проверить задачу директора",
            description="Должна быть видна автору",
            assignment_type=Task.AssignmentType.INDIVIDUAL,
            assigned_to=assignee,
            created_by=self.user,
        )

        response = self.client.get(
            "/api/tasks/?all_shops=true",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        items = payload["items"] if isinstance(payload, dict) else payload
        self.assertIn(task.id, {item["id"] for item in items})

    def test_task_summary_uses_director_visible_scope_not_only_my_tasks(self):
        second_shop = Shop.objects.create(
            name="Second Shop",
            code="TEST02",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        assignee = User.objects.create_user(
            username="summary-worker",
            password="pass12345",
            first_name="Summary",
            last_name="Worker",
            role=self.role,
            current_shop=second_shop,
        )
        assignee.shops.add(second_shop)
        Task.objects.create(
            title="Контрольная задача директора",
            description="Не назначена директору лично",
            assignment_type=Task.AssignmentType.INDIVIDUAL,
            assigned_to=assignee,
            created_by=self.user,
        )

        response = self.client.get(
            "/api/tasks/my-tasks-summary?all_shops=true",
            **self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["total_tasks"], 1)
        self.assertEqual(payload["status_breakdown"][Task.Status.PENDING], 1)
