from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class Customer(models.Model):
    """Модель клиента - общая для всех магазинов"""

    class CustomerSource(models.TextChoices):
        WEBSITE = "website", "Сайт"
        SOCIAL = "social", "Социальные сети"
        REFERRAL = "referral", "Рекомендация"
        ADVERTISING = "advertising", "Реклама"
        WALK_IN = "walk_in", "Зашел с улицы"
        OTHER = "other", "Другое"

    first_name = models.CharField("Имя", max_length=50)
    last_name = models.CharField("Фамилия", max_length=50)
    middle_name = models.CharField("Отчество", max_length=50, blank=True)

    phone = PhoneNumberField("Телефон", unique=True)
    email = models.EmailField("Email", blank=True)

    source = models.CharField(
        "Откуда узнали", max_length=20, choices=CustomerSource.choices, blank=True
    )
    source_details = models.CharField("Детали источника", max_length=200, blank=True)

    # Дополнительная информация
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    notes = models.TextField("Заметки", blank=True)

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_customers",
        verbose_name="Создал",
    )

    # Статистика
    orders_count = models.PositiveIntegerField("Количество заказов", default=0)
    total_spent = models.DecimalField(
        "Общая сумма заказов", max_digits=12, decimal_places=2, default=0
    )

    class PreferredChannel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"

    preferred_channel = models.CharField(
        "Предпочтительный канал",
        max_length=10,
        choices=PreferredChannel.choices,
        blank=True,
    )
    marketing_consent = models.BooleanField("Согласие на коммуникации", default=False)

    class Meta:
        db_table = "customers"
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.phone})"

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    def update_statistics(self):
        """Обновление статистики клиента"""
        from orders.models import Order

        orders = Order.objects.filter(customer=self)

        self.orders_count = orders.count()
        self.total_spent = sum(
            order.final_cost or order.cost_estimate
            for order in orders
            if order.final_cost or order.cost_estimate
        )
        self.save(update_fields=["orders_count", "total_spent"])


class CustomerShopHistory(models.Model):
    """История взаимодействия клиента с конкретным магазином"""

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="shop_history"
    )
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE)

    first_visit = models.DateTimeField("Первое посещение", auto_now_add=True)
    last_visit = models.DateTimeField("Последнее посещение", auto_now=True)
    visits_count = models.PositiveIntegerField("Количество посещений", default=1)

    class Meta:
        db_table = "customer_shop_history"
        unique_together = ["customer", "shop"]
        verbose_name = "История клиента в магазине"
        verbose_name_plural = "История клиентов в магазинах"
