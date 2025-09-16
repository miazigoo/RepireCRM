from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Order(models.Model):
    """Модель заказа"""

    class StatusChoices(models.TextChoices):
        RECEIVED = 'received', 'Принят'
        DIAGNOSED = 'diagnosed', 'Диагностирован'
        WAITING_PARTS = 'waiting_parts', 'Ожидание запчастей'
        IN_REPAIR = 'in_repair', 'В ремонте'
        TESTING = 'testing', 'Тестирование'
        READY = 'ready', 'Готов к выдаче'
        COMPLETED = 'completed', 'Выдан'
        CANCELLED = 'cancelled', 'Отменен'

    class PriorityChoices(models.TextChoices):
        LOW = 'low', 'Низкий'
        NORMAL = 'normal', 'Обычный'
        HIGH = 'high', 'Высокий'
        URGENT = 'urgent', 'Срочный'

    # Основная информация
    shop = models.ForeignKey(
        'shops.Shop',
        on_delete=models.PROTECT,
        verbose_name="Магазин"
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        verbose_name="Клиент"
    )
    device = models.ForeignKey(
        'device.Device',
        on_delete=models.PROTECT,
        verbose_name="Устройство"
    )

    # Номер заказа
    order_number = models.CharField("Номер заказа", max_length=20, unique=True)

    # Статус и приоритет
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.RECEIVED
    )
    priority = models.CharField(
        "Приоритет",
        max_length=10,
        choices=PriorityChoices.choices,
        default=PriorityChoices.NORMAL
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
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    final_cost = models.DecimalField(
        "Итоговая стоимость",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    prepayment = models.DecimalField(
        "Предоплата",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Сотрудники
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='created_orders',
        verbose_name="Принял заказ"
    )
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders',
        verbose_name="Назначен исполнитель"
    )

    # Временные метки
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    estimated_completion = models.DateTimeField(
        "Планируемая дата готовности",
        null=True,
        blank=True
    )
    completed_at = models.DateTimeField(
        "Дата завершения",
        null=True,
        blank=True
    )

    # Дополнительные услуги
    additional_services = models.ManyToManyField(
        'AdditionalService',
        through='OrderService',
        blank=True,
        verbose_name="Дополнительные услуги"
    )

    # Заметки
    notes = models.TextField("Внутренние заметки", blank=True)

    class Meta:
        db_table = 'orders'
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shop', 'status']),
            models.Index(fields=['customer']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Заказ {self.order_number} - {self.customer.full_name}"

    @property
    def total_cost(self):
        """Общая стоимость заказа включая дополнительные услуги"""
        base_cost = self.final_cost or self.cost_estimate
        services_cost = sum(
            service.price * service.quantity
            for service in self.orderservice_set.all()
        )
        return base_cost + services_cost

    @property
    def remaining_payment(self):
        """Остаток к доплате"""
        return max(0, self.total_cost - self.prepayment)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        """Генерация номера заказа"""
        from django.db.models import Max

        shop_settings = getattr(self.shop, 'settings', None)
        prefix = shop_settings.order_number_prefix if shop_settings else 'ORD'

        # Получаем последний номер заказа для магазина
        last_order = Order.objects.filter(
            shop=self.shop,
            order_number__startswith=prefix
        ).aggregate(Max('id'))['id__max'] or 0

        return f"{prefix}-{self.shop.code}-{last_order + 1:06d}"


class AdditionalService(models.Model):
    """Дополнительные услуги"""

    class ServiceCategory(models.TextChoices):
        ACCESSORIES = 'accessories', 'Аксессуары'
        PROTECTION = 'protection', 'Защитные покрытия'
        SOFTWARE = 'software', 'Программное обеспечение'
        CLEANING = 'cleaning', 'Чистка'
        OTHER = 'other', 'Прочее'

    name = models.CharField("Название", max_length=100)
    category = models.CharField(
        "Категория",
        max_length=20,
        choices=ServiceCategory.choices
    )
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField(
        "Цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    is_active = models.BooleanField("Активна", default=True)

    # Привязка к магазинам
    shops = models.ManyToManyField(
        'shops.Shop',
        verbose_name="Доступна в магазинах",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'additional_services'
        verbose_name = 'Дополнительная услуга'
        verbose_name_plural = 'Дополнительные услуги'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class OrderService(models.Model):
    """Промежуточная модель для дополнительных услуг в заказе"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    service = models.ForeignKey(AdditionalService, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField(
        "Цена за единицу",
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        db_table = 'order_services'
        unique_together = ['order', 'service']
        verbose_name = 'Услуга в заказе'
        verbose_name_plural = 'Услуги в заказах'

    @property
    def total_price(self):
        return self.price * self.quantity