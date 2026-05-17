from datetime import timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max
from django.utils import timezone
from sequences import get_next_value

from finance.fiscal_constants import FiscalMeasure, FiscalPaymentSubject, FiscalVatCode


class Order(models.Model):
    """Модель заказа"""

    class StatusChoices(models.TextChoices):
        RECEIVED = "received", "Принят"
        DIAGNOSED = "diagnosed", "Диагностирован"
        WAITING_PARTS = "waiting_parts", "Ожидание запчастей"
        IN_REPAIR = "in_repair", "В ремонте"
        TESTING = "testing", "Тестирование"
        READY = "ready", "Готов к выдаче"
        COMPLETED = "completed", "Выдан"
        CANCELLED = "cancelled", "Отменен"

    class PriorityChoices(models.TextChoices):
        LOW = "low", "Низкий"
        NORMAL = "normal", "Обычный"
        HIGH = "high", "Высокий"
        URGENT = "urgent", "Срочный"

    # Основная информация
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.PROTECT, verbose_name="Магазин"
    )
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, verbose_name="Клиент"
    )
    device = models.ForeignKey(
        "device.Device", on_delete=models.PROTECT, verbose_name="Устройство"
    )

    # Номер заказа
    order_number = models.CharField("Номер заказа", max_length=20, unique=True)

    # Статус и приоритет
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.RECEIVED,
    )
    priority = models.CharField(
        "Приоритет",
        max_length=10,
        choices=PriorityChoices.choices,
        default=PriorityChoices.NORMAL,
    )

    # Описание проблемы и работы
    problem_description = models.TextField("Описание проблемы")
    diagnosis = models.TextField("Диагноз", blank=True)
    work_description = models.TextField("Описание выполненных работ", blank=True)

    # Комплектация и состояние
    accessories = models.TextField("Комплектация", blank=True)
    device_condition = models.TextField("Состояние устройства", blank=True)

    # Стоимость
    cost_estimate = models.DecimalField(
        "Предварительная стоимость",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    final_cost = models.DecimalField(
        "Итоговая стоимость",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    prepayment = models.DecimalField(
        "Предоплата",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Сотрудники
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="created_orders",
        verbose_name="Принял заказ",
    )
    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
        verbose_name="Назначен исполнитель",
    )

    # Временные метки
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    estimated_completion = models.DateTimeField(
        "Планируемая дата готовности", null=True, blank=True
    )
    completed_at = models.DateTimeField("Дата завершения", null=True, blank=True)

    # Дополнительные услуги
    additional_services = models.ManyToManyField(
        "AdditionalService",
        through="OrderService",
        blank=True,
        verbose_name="Дополнительные услуги",
    )

    # Заметки
    notes = models.TextField("Внутренние заметки", blank=True)
    sla_on_time = models.BooleanField("В срок", null=True, blank=True)
    sla_delay_minutes = models.IntegerField("Отклонение, мин", null=True, blank=True)
    # положительные — опоздание, отрицательные — раньше, 0 — точно в срок

    # Гарантия и гарантийные обращения
    warranty_days = models.PositiveIntegerField("Гарантия (дней)", default=90)
    warranty_until = models.DateTimeField("Гарантия до", null=True, blank=True)
    is_warranty_case = models.BooleanField("Гарантийный случай", default=False)
    warranty_parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warranty_cases",
        verbose_name="Исходный заказ по гарантии",
    )
    warranty_reason = models.TextField("Причина гарантийного обращения", blank=True)
    warranty_resolution = models.TextField("Решение по гарантии", blank=True)

    class Meta:
        db_table = "orders"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "status"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["order_number"]),
            models.Index(fields=["completed_at", "sla_on_time"]),
            models.Index(fields=["estimated_completion"]),
            models.Index(fields=["is_warranty_case", "status"]),
            models.Index(fields=["warranty_parent"]),
            models.Index(fields=["warranty_until"]),
        ]

    def __str__(self):
        return f"Заказ {self.order_number} - {self.customer.full_name}"

    @staticmethod
    def _as_money(value):
        if value is None:
            return Decimal("0.00")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @property
    def total_cost(self):
        """Общая стоимость заказа с услугами и примененными скидками."""
        base_cost = self._as_money(
            self.final_cost if self.final_cost is not None else self.cost_estimate
        )
        services_cost = sum(
            (
                self._as_money(service.price) * self._as_money(service.quantity)
                for service in self.orderservice_set.all()
            ),
            Decimal("0.00"),
        )
        return max(Decimal("0.00"), base_cost + services_cost - self.discount_total)

    @property
    def subtotal_before_discount(self):
        """Сумма заказа до скидок."""
        base_cost = self._as_money(
            self.final_cost if self.final_cost is not None else self.cost_estimate
        )
        services_cost = sum(
            (
                self._as_money(service.price) * self._as_money(service.quantity)
                for service in self.orderservice_set.all()
            ),
            Decimal("0.00"),
        )
        return base_cost + services_cost

    @property
    def discount_total(self):
        """Суммарная скидка заказа."""
        return sum(
            (discount.amount for discount in self.discounts.all()),
            Decimal("0.00"),
        )

    @property
    def remaining_payment(self):
        """Остаток к доплате"""
        return max(Decimal("0.00"), self.total_cost - self._as_money(self.prepayment))

    @property
    def warranty_active(self):
        """Действует ли гарантия на текущий момент."""
        return bool(
            self.warranty_until
            and self.status == self.StatusChoices.COMPLETED
            and self.warranty_until >= timezone.now()
        )

    def _generate_order_number(self):
        """Генерация номера заказа"""
        shop_settings = getattr(self.shop, "settings", None)
        prefix = shop_settings.order_number_prefix if shop_settings else "ORD"
        seq = get_next_value(f"order-{self.shop.code}")
        return f"{prefix}-{self.shop.code}-{seq:06d}"

    def save(self, *args, **kwargs):
        # Бизнес-правило: нельзя закрыть без final_cost
        if self.status == self.StatusChoices.COMPLETED and self.final_cost is None:
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "Нельзя закрыть заказ без итоговой стоимости (final_cost)"
            )

        if not self.order_number:
            self.order_number = self._generate_order_number()

        if self.status == self.StatusChoices.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(set(update_fields) | {"completed_at"})

        if (
            self.status == self.StatusChoices.COMPLETED
            and self.completed_at
            and self.warranty_days
            and not self.warranty_until
        ):
            self.warranty_until = self.completed_at + timedelta(days=self.warranty_days)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(set(update_fields) | {"warranty_until"})

        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """История переходов статусов заказа."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name="Заказ",
    )
    old_status = models.CharField(
        "Старый статус",
        max_length=20,
        choices=Order.StatusChoices.choices,
        blank=True,
    )
    new_status = models.CharField(
        "Новый статус",
        max_length=20,
        choices=Order.StatusChoices.choices,
    )
    comment = models.TextField("Комментарий", blank=True)
    changed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
        verbose_name="Кто изменил",
    )
    changed_at = models.DateTimeField("Дата изменения", auto_now_add=True)

    class Meta:
        db_table = "order_status_history"
        verbose_name = "История статуса заказа"
        verbose_name_plural = "История статусов заказов"
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["order", "-changed_at"]),
            models.Index(fields=["new_status"]),
        ]


class OrderAuditLog(models.Model):
    """Аудит важных действий с заказом."""

    class ActionChoices(models.TextChoices):
        CREATED = "created", "Создан"
        UPDATED = "updated", "Обновлен"
        STATUS_CHANGED = "status_changed", "Изменен статус"
        STAGE_ADDED = "stage_added", "Добавлен этап"
        STAGE_UPDATED = "stage_updated", "Обновлен этап"
        APPROVAL_REQUESTED = "approval_requested", "Запрошено согласование"
        APPROVAL_DECIDED = "approval_decided", "Решение по согласованию"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        verbose_name="Заказ",
    )
    action = models.CharField("Действие", max_length=40, choices=ActionChoices.choices)
    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_audit_logs",
        verbose_name="Пользователь",
    )
    message = models.CharField("Описание", max_length=255)
    changes = models.JSONField("Изменения", default=dict, blank=True)
    created_at = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        db_table = "order_audit_logs"
        verbose_name = "Запись аудита заказа"
        verbose_name_plural = "Аудит заказов"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "-created_at"]),
            models.Index(fields=["action"]),
        ]


class RepairStage(models.Model):
    """Произвольный этап ремонта с фотофиксацией."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="repair_stages",
        verbose_name="Заказ",
    )
    title = models.CharField("Название этапа", max_length=120)
    description = models.TextField("Описание", blank=True)
    photo = models.ImageField("Фото", upload_to="repair_stages/%Y/%m/", blank=True)
    customer_visible = models.BooleanField("Видно клиенту", default=True)
    position = models.PositiveIntegerField("Порядок", default=0)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="repair_stages",
        verbose_name="Кто добавил",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        db_table = "repair_stages"
        verbose_name = "Этап ремонта"
        verbose_name_plural = "Этапы ремонта"
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["order", "position"]),
            models.Index(fields=["order", "customer_visible"]),
        ]

    @property
    def photo_url(self):
        if not self.photo:
            return None
        return self.photo.url

    def save(self, *args, **kwargs):
        if not self.position:
            max_position = (
                RepairStage.objects.filter(order=self.order).aggregate(Max("position"))[
                    "position__max"
                ]
                or 0
            )
            self.position = max_position + 1
        super().save(*args, **kwargs)


class OrderApproval(models.Model):
    """Согласование диагностики, стоимости или работ с клиентом."""

    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Ожидает решения"
        APPROVED = "approved", "Согласовано"
        REJECTED = "rejected", "Отклонено"
        CANCELLED = "cancelled", "Отменено"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="approvals",
        verbose_name="Заказ",
    )
    title = models.CharField("Что согласовываем", max_length=160)
    description = models.TextField("Описание", blank=True)
    amount = models.DecimalField(
        "Сумма",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    customer_comment = models.TextField("Комментарий клиента", blank=True)
    requested_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_order_approvals",
        verbose_name="Кто запросил",
    )
    decided_at = models.DateTimeField("Дата решения", null=True, blank=True)
    created_at = models.DateTimeField("Дата запроса", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        db_table = "order_approvals"
        verbose_name = "Согласование заказа"
        verbose_name_plural = "Согласования заказов"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["created_at"]),
        ]

    @property
    def status_display(self):
        return self.get_status_display()


class AdditionalService(models.Model):
    """Дополнительные услуги"""

    class ServiceCategory(models.TextChoices):
        ACCESSORIES = "accessories", "Аксессуары"
        PROTECTION = "protection", "Защитные покрытия"
        SOFTWARE = "software", "Программное обеспечение"
        CLEANING = "cleaning", "Чистка"
        OTHER = "other", "Прочее"

    name = models.CharField("Название", max_length=100)
    category = models.CharField(
        "Категория", max_length=20, choices=ServiceCategory.choices
    )
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField(
        "Цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_active = models.BooleanField("Активна", default=True)
    fiscal_subject = models.CharField(
        "Фискальный предмет расчета",
        max_length=30,
        choices=FiscalPaymentSubject.choices,
        default=FiscalPaymentSubject.SERVICE,
    )
    fiscal_vat_code = models.CharField(
        "НДС для фискального чека",
        max_length=20,
        choices=FiscalVatCode.choices,
        blank=True,
        default="",
        help_text="Если пусто, используется НДС услуг из настроек филиала",
    )
    fiscal_measure = models.CharField(
        "Единица измерения для ККМ",
        max_length=30,
        choices=FiscalMeasure.choices,
        default=FiscalMeasure.SERVICE,
    )

    # Привязка к магазинам
    shops = models.ManyToManyField(
        "shops.Shop", verbose_name="Доступна в магазинах", blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "additional_services"
        verbose_name = "Дополнительная услуга"
        verbose_name_plural = "Дополнительные услуги"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class OrderService(models.Model):
    """Промежуточная модель для дополнительных услуг в заказе"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    service = models.ForeignKey(AdditionalService, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField("Цена за единицу", max_digits=10, decimal_places=2)

    class Meta:
        db_table = "order_services"
        unique_together = ["order", "service"]
        verbose_name = "Услуга в заказе"
        verbose_name_plural = "Услуги в заказах"

    @property
    def total_price(self):
        return self.price * self.quantity


class RepairService(models.Model):
    """Типовая ремонтная работа по бренду/модели"""

    code = models.CharField("Код", max_length=50, unique=True)
    name = models.CharField("Название", max_length=200)

    device_type = models.ForeignKey(
        "device.DeviceType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Тип устройства",
    )
    brand = models.ForeignKey(
        "device.DeviceBrand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Бренд",
    )
    model = models.ForeignKey(
        "device.DeviceModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Модель",
    )

    default_price = models.DecimalField(
        "Базовая цена", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    avg_hours = models.DecimalField(
        "Среднее время (ч)", max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    warranty_days = models.PositiveIntegerField("Гарантия (дней)", default=90)

    diagnostics_required = models.BooleanField("Требует диагностики", default=False)
    notes = models.TextField("Примечания", blank=True)

    # Ограничение по магазинам (если пусто — доступно всем)
    shops = models.ManyToManyField("shops.Shop", blank=True)

    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "repair_services"
        verbose_name = "Типовая ремонтная работа"
        verbose_name_plural = "Типовые ремонтные работы"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["brand", "model"]),
            models.Index(fields=["device_type", "brand"]),
        ]

    def __str__(self):
        p = []
        if self.brand:
            p.append(self.brand.name)
        if self.model:
            p.append(self.model.name)
        return f"{self.name} ({' '.join(p)})" if p else self.name
