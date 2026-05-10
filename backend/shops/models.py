import math

from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Shop(models.Model):
    """Модель магазина/филиала"""

    name = models.CharField("Название", max_length=100)
    code = models.CharField(
        "Код магазина",
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^[A-Z0-9]+$", "Только заглавные буквы и цифры")],
    )
    city = models.CharField(
        "Город",
        max_length=100,
        blank=True,
        help_text="Для фильтра на лендинге; если пусто — берём из начала адреса",
    )
    address = models.TextField("Адрес", blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)

    is_active = models.BooleanField("Активен", default=True)
    timezone = models.CharField("Часовой пояс", max_length=50, default="Europe/Moscow")

    currency = models.CharField("Валюта", max_length=3, default="RUB")
    tax_rate = models.DecimalField(
        "Налоговая ставка (%)", max_digits=5, decimal_places=2, default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shops"
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Organization(models.Model):
    """Юридическое лицо (общие реквизиты, используются несколькими точками)"""

    name = models.CharField("Название юр. лица", max_length=200)
    inn = models.CharField("ИНН", max_length=20, blank=True)
    kpp = models.CharField("КПП", max_length=20, blank=True)
    address = models.CharField("Юр. адрес", max_length=300, blank=True)
    phone = models.CharField("Телефон", max_length=50, blank=True)
    email = models.EmailField("Email", blank=True)
    bank_details = models.TextField("Банковские реквизиты", blank=True)
    website = models.CharField("Сайт", max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"
        verbose_name = "Организация"
        verbose_name_plural = "Организации"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ShopSettings(models.Model):
    """Настройки магазина"""

    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name="settings")

    # Общие настройки
    order_number_prefix = models.CharField(
        "Префикс номера заказа", max_length=5, default="ORD"
    )
    auto_order_numbering = models.BooleanField(
        "Автоматическая нумерация заказов", default=True
    )
    sms_notifications = models.BooleanField("SMS уведомления", default=False)
    email_notifications = models.BooleanField("Email уведомления", default=True)
    work_hours_start = models.TimeField("Начало работы", null=True, blank=True)
    work_hours_end = models.TimeField("Конец работы", null=True, blank=True)
    work_days = models.CharField("Рабочие дни", max_length=20, default="1,2,3,4,5")
    pos_barcode_enabled = models.BooleanField("POS с ШК включен", default=False)

    # Юр. лицо (ссылка)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Организация",
    )

    # Футер чеков/квитанций
    receipt_footer_text = models.CharField(
        "Футер чека/квит.", max_length=200, blank=True
    )

    # Field visit settings
    field_visit_enabled = models.BooleanField("Выезд мастера включён", default=False)
    field_visit_service_name = models.CharField(
        "Название услуги", max_length=100, default="Выезд мастера"
    )
    field_visit_base_price = models.DecimalField(
        "Базовая стоимость", max_digits=10, decimal_places=2, default=0
    )
    field_visit_out_of_zone_price = models.DecimalField(
        "Стоимость за пределами зон", max_digits=10, decimal_places=2, default=0
    )
    field_visit_description = models.TextField("Описание услуги", blank=True)
    field_visit_zones = models.JSONField("Зоны обслуживания", default=list, blank=True)
    # zones: [{"id": "uuid", "name": "Центр", "price": 0.0,
    #           "geometry": {"type": "Polygon", "coordinates": [...]}}]
    field_visit_advance_days = models.PositiveIntegerField(
        "Предварительная запись за (дней)", default=1
    )

    class Meta:
        db_table = "shop_settings"
        verbose_name = "Настройки магазина"
        verbose_name_plural = "Настройки магазинов"


class SubscriptionPlan(models.Model):
    """Тариф SaaS-подписки."""

    class BillingPeriod(models.TextChoices):
        TRIAL = "trial", "Пробный период"
        MONTH = "month", "Месяц"
        HALF_YEAR = "half_year", "Полгода"
        YEAR = "year", "Год"

    code = models.CharField("Код", max_length=30, unique=True)
    name = models.CharField("Название", max_length=80)
    billing_period = models.CharField(
        "Период", max_length=20, choices=BillingPeriod.choices
    )
    duration_days = models.PositiveIntegerField("Длительность, дней")
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        db_table = "subscription_plans"
        verbose_name = "Тариф подписки"
        verbose_name_plural = "Тарифы подписки"
        ordering = ["duration_days"]

    def __str__(self):
        return self.name


class OrganizationSubscription(models.Model):
    """Текущая подписка организации."""

    class Status(models.TextChoices):
        TRIAL = "trial", "Пробный период"
        ACTIVE = "active", "Активна"
        EXPIRED = "expired", "Истекла"
        CANCELLED = "cancelled", "Отменена"

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="Организация",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        verbose_name="Тариф",
    )
    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.TRIAL
    )
    started_at = models.DateTimeField("Дата начала")
    expires_at = models.DateTimeField("Дата окончания")
    last_notice_bucket = models.PositiveIntegerField(
        "Последний bucket уведомления", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_subscriptions"
        verbose_name = "Подписка организации"
        verbose_name_plural = "Подписки организаций"
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["expires_at"]),
        ]

    @property
    def total_days(self):
        seconds = (self.expires_at - self.started_at).total_seconds()
        return max(1, math.ceil(seconds / 86400))

    @property
    def remaining_days(self):
        seconds = (self.expires_at - timezone.now()).total_seconds()
        return max(0, math.ceil(seconds / 86400))

    @property
    def remaining_percent(self):
        return max(0, min(100, round((self.remaining_days / self.total_days) * 100)))

    @property
    def color_bucket(self):
        percent = self.remaining_percent
        if percent == 100:
            return 100
        return max(0, min(90, (percent // 10) * 10))

    @property
    def color_hex(self):
        return SUBSCRIPTION_COLOR_SCALE[self.color_bucket]

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()


SUBSCRIPTION_COLOR_SCALE = {
    100: "#1b8f3a",
    90: "#2fa84f",
    80: "#62b947",
    70: "#94c83d",
    60: "#c4d137",
    50: "#e2c438",
    40: "#f0a832",
    30: "#ef842f",
    20: "#e95f34",
    10: "#d93f32",
    0: "#b91c1c",
}
