from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class TaskCategory(models.Model):
    """Категории задач"""

    name = models.CharField("Название", max_length=100, unique=True)
    description = models.TextField("Описание", blank=True)
    color = models.CharField("Цвет", max_length=7, default="#007bff")
    icon = models.CharField("Иконка", max_length=50, blank=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Категория задач"
        verbose_name_plural = "Категории задач"

    def __str__(self):
        return self.name


class Task(models.Model):
    """Задачи"""

    class Priority(models.TextChoices):
        LOW = "low", "Низкий"
        NORMAL = "normal", "Обычный"
        HIGH = "high", "Высокий"
        URGENT = "urgent", "Срочный"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        IN_PROGRESS = "in_progress", "В работе"
        COMPLETED = "completed", "Выполнена"
        CANCELLED = "cancelled", "Отменена"
        OVERDUE = "overdue", "Просрочена"

    class AssignmentType(models.TextChoices):
        INDIVIDUAL = "individual", "Конкретному сотруднику"
        SHOP = "shop", "Магазину"
        ALL_SHOPS = "all_shops", "Всем магазинам"
        ROLE = "role", "По роли"

    # Основная информация
    title = models.CharField("Заголовок", max_length=200)
    description = models.TextField("Описание")
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Категория",
    )

    # Приоритет и статус
    priority = models.CharField(
        "Приоритет", max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        "Статус", max_length=15, choices=Status.choices, default=Status.PENDING
    )

    # Назначение
    assignment_type = models.CharField(
        "Тип назначения", max_length=15, choices=AssignmentType.choices
    )

    # Исполнители (в зависимости от типа назначения)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        verbose_name="Назначено пользователю",
    )
    assigned_shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Назначено магазину",
    )
    assigned_role = models.ForeignKey(
        "users.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Назначено роли",
    )

    # Связанные объекты
    related_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Связанный заказ",
    )
    related_customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Связанный клиент",
    )

    # Даты и время
    due_date = models.DateTimeField("Срок выполнения", null=True, blank=True)
    estimated_hours = models.DecimalField(
        "Оценка времени (часы)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    actual_hours = models.DecimalField(
        "Фактическое время (часы)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Прогресс
    progress_percent = models.PositiveIntegerField("Прогресс %", default=0)

    # Вложения и комментарии
    attachments = models.JSONField("Вложения", default=list, blank=True)

    # Повторяющиеся задачи
    is_recurring = models.BooleanField("Повторяющаяся", default=False)
    recurrence_pattern = models.JSONField("Шаблон повторения", default=dict, blank=True)
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Родительская задача",
    )

    # Автор и даты
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_tasks",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Выполнение
    started_at = models.DateTimeField("Начато", null=True, blank=True)
    completed_at = models.DateTimeField("Завершено", null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_tasks",
        verbose_name="Выполнил",
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["assigned_shop", "status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["status", "priority"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        if self.due_date and self.status not in ["completed", "cancelled"]:
            return timezone.now() > self.due_date
        return False

    def get_assignees(self):
        """Получить всех исполнителей задачи"""
        assignees = []

        if self.assignment_type == self.AssignmentType.INDIVIDUAL and self.assigned_to:
            assignees.append(self.assigned_to)

        elif self.assignment_type == self.AssignmentType.SHOP and self.assigned_shop:
            # Все пользователи магазина
            from users.models import UserShop

            shop_users = User.objects.filter(
                usershop__shop=self.assigned_shop, is_active=True
            )
            assignees.extend(shop_users)

        elif self.assignment_type == self.AssignmentType.ALL_SHOPS:
            # Все активные пользователи
            assignees.extend(User.objects.filter(is_active=True))

        elif self.assignment_type == self.AssignmentType.ROLE and self.assigned_role:
            # Пользователи с определенной ролью
            assignees.extend(
                User.objects.filter(role=self.assigned_role, is_active=True)
            )

        return assignees

    def save(self, *args, **kwargs):
        # Автоматически обновляем статус на просроченный
        if self.is_overdue and self.status == self.Status.PENDING:
            self.status = self.Status.OVERDUE

        # Устанавливаем даты начала и завершения
        if self.status == self.Status.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()

        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
            self.progress_percent = 100

        super().save(*args, **kwargs)


class TaskComment(models.Model):
    """Комментарии к задачам"""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    text = models.TextField("Текст комментария")
    attachments = models.JSONField("Вложения", default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Комментарий к задаче"
        verbose_name_plural = "Комментарии к задачам"
        ordering = ["created_at"]


class TaskTimeLog(models.Model):
    """Учет времени по задачам"""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="time_logs")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    started_at = models.DateTimeField("Начало")
    ended_at = models.DateTimeField("Окончание", null=True, blank=True)
    duration_minutes = models.PositiveIntegerField("Длительность (мин)", default=0)

    description = models.TextField("Описание работы", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лог времени"
        verbose_name_plural = "Логи времени"
        ordering = ["-started_at"]

    def save(self, *args, **kwargs):
        if self.ended_at and self.started_at:
            delta = self.ended_at - self.started_at
            self.duration_minutes = int(delta.total_seconds() / 60)
        super().save(*args, **kwargs)


class TaskTemplate(models.Model):
    """Шаблоны задач"""

    name = models.CharField("Название", max_length=200)
    title_template = models.CharField("Шаблон заголовка", max_length=200)
    description_template = models.TextField("Шаблон описания")
    category = models.ForeignKey(
        TaskCategory, on_delete=models.SET_NULL, null=True, blank=True
    )

    default_priority = models.CharField(
        "Приоритет по умолчанию",
        max_length=10,
        choices=Task.Priority.choices,
        default=Task.Priority.NORMAL,
    )
    default_assignment_type = models.CharField(
        "Тип назначения по умолчанию",
        max_length=15,
        choices=Task.AssignmentType.choices,
        default=Task.AssignmentType.INDIVIDUAL,
    )

    estimated_hours = models.DecimalField(
        "Оценка времени (часы)", max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Автоматическое создание
    auto_create_trigger = models.CharField(
        "Триггер автосоздания",
        max_length=50,
        blank=True,
        help_text="Например: order_created, customer_registered",
    )

    is_active = models.BooleanField("Активен", default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Шаблон задачи"
        verbose_name_plural = "Шаблоны задач"

    def create_task(self, context=None, **kwargs):
        """Создать задачу из шаблона"""
        context = context or {}

        # Рендерим шаблоны с контекстом
        title = self.title_template.format(**context)
        description = self.description_template.format(**context)

        task_data = {
            "title": title,
            "description": description,
            "category": self.category,
            "priority": self.default_priority,
            "assignment_type": self.default_assignment_type,
            "estimated_hours": self.estimated_hours,
            **kwargs,
        }

        return Task.objects.create(**task_data)
