from django.db import models
from django.db.models import Q
from django.utils import timezone

from inventory.models import StockBalance
from notifications.services import notification_service

from .models import Task, TaskCategory, TaskTemplate


class TaskService:
    """Сервис для работы с задачами"""

    def notify_assignees(self, task):
        """Уведомить исполнителей о новой задаче"""
        assignees = task.get_assignees()

        for assignee in assignees:
            notification_service.create_notification(
                notification_type_code="task_assigned",
                title=f"Новая задача: {task.title}",
                message=f'Вам назначена задача "{task.title}"',
                recipient=assignee,
                priority="normal",
                related_object_type="task",
                related_object_id=task.id,
                action_url=f"/tasks/{task.id}",
                data={
                    "task_id": task.id,
                    "task_title": task.title,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                },
            )

    def notify_status_change(self, task, old_status):
        """Уведомить о смене статуса задачи"""
        # Уведомляем создателя задачи
        if task.created_by:
            notification_service.create_notification(
                notification_type_code="task_status_change",
                title=f"Изменен статус задачи: {task.title}",
                message=f'Статус изменен с "{task.get_status_display()}" на "{old_status}"',
                recipient=task.created_by,
                priority="low",
                related_object_type="task",
                related_object_id=task.id,
                action_url=f"/tasks/{task.id}",
            )

    def notify_new_comment(self, task, comment):
        """Уведомить о новом комментарии"""
        # Собираем всех участников обсуждения
        participants = set()
        participants.add(task.created_by)
        participants.update(task.get_assignees())
        participants.update(task.comments.values_list("author", flat=True))

        # Исключаем автора комментария
        participants.discard(comment.author)

        for participant in participants:
            notification_service.create_notification(
                notification_type_code="task_comment",
                title=f"Новый комментарий к задаче: {task.title}",
                message=f"{comment.author.get_full_name()} добавил комментарий",
                recipient=participant,
                priority="low",
                related_object_type="task",
                related_object_id=task.id,
                action_url=f"/tasks/{task.id}",
            )

    def auto_create_tasks_for_order(self, order):
        """Автоматическое создание задач при создании заказа"""
        # Найти шаблоны с триггером order_created
        templates = TaskTemplate.objects.filter(
            auto_create_trigger="order_created", is_active=True
        )

        for template in templates:
            context = {
                "order_number": order.order_number,
                "customer_name": order.customer.full_name,
                "device": f"{order.device.model.brand.name} {order.device.model.name}",
                "shop_name": order.shop.name,
            }

            template.create_task(
                context=context,
                created_by=order.created_by,
                related_order=order,
                assignment_type="shop",
                assigned_shop=order.shop,
            )

    def check_overdue_tasks(self):
        """Проверить просроченные задачи (для cron)"""
        overdue_tasks = Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=[Task.Status.PENDING, Task.Status.IN_PROGRESS],
        ).exclude(status=Task.Status.OVERDUE)

        for task in overdue_tasks:
            task.status = Task.Status.OVERDUE
            task.save()

            # Уведомляем о просрочке
            assignees = task.get_assignees()
            for assignee in assignees:
                notification_service.create_notification(
                    notification_type_code="task_overdue",
                    title=f"Задача просрочена: {task.title}",
                    message=f'Задача "{task.title}" просрочена на {(timezone.now() - task.due_date).days} дней',
                    recipient=assignee,
                    priority="high",
                    related_object_type="task",
                    related_object_id=task.id,
                    action_url=f"/tasks/{task.id}",
                )

    def create_low_stock_tasks(self):
        """Создать/обновить задачи по товарам с низким остатком"""
        low_qs = (
            StockBalance.objects.select_related("shop", "item")
            .filter(item__is_active=True)
            .filter(
                Q(quantity__lte=models.F("min_quantity"))
                | Q(available_quantity__lte=models.F("min_quantity"))
            )
        )

        # Категория задач
        category, _ = TaskCategory.objects.get_or_create(
            name="Склад: Перезаказ/Проверка остатков",
            defaults={
                "description": "Автозадачи по низкому остатку",
                "color": "#dc3545",
            },
        )

        created = 0
        for b in low_qs:
            title = f"Перезаказ: {b.item.name} ({b.item.sku}) [{b.shop.name}]"
            # Ищем незакрытую задачу по этому товару/магазину
            existing = Task.objects.filter(
                title=title,
                status__in=[
                    Task.Status.PENDING,
                    Task.Status.IN_PROGRESS,
                    Task.Status.OVERDUE,
                ],
            ).first()
            if existing:
                continue

            task = Task.objects.create(
                title=title,
                description=(
                    f"Остаток: {b.quantity}, доступно: {b.available_quantity}. "
                    f"Мин. остаток: {b.min_quantity}. "
                    f"Рекомендуется перезаказ до {b.max_quantity}."
                ),
                category=category,
                priority=Task.Priority.HIGH,
                status=Task.Status.PENDING,
                assignment_type=Task.AssignmentType.SHOP,
                assigned_shop=b.shop,
                created_by=None,  # системная задача; при желании — указать директора
                due_date=timezone.now() + timezone.timedelta(days=1),
            )
            created += 1
        return created
