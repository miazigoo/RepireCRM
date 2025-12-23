from django.core.validators import RegexValidator
from django.db import models


class Shop(models.Model):
    """Модель магазина/филиала"""

    name = models.CharField("Название", max_length=100)
    code = models.CharField(
        "Код магазина",
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^[A-Z0-9]+$", "Только заглавные буквы и цифры")],
    )
    address = models.TextField("Адрес", blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)

    # Настройки магазина
    is_active = models.BooleanField("Активен", default=True)
    timezone = models.CharField("Часовой пояс", max_length=50, default="Europe/Moscow")

    # Финансовые настройки
    currency = models.CharField("Валюта", max_length=3, default="RUB")
    tax_rate = models.DecimalField(
        "Налоговая ставка (%)", max_digits=5, decimal_places=2, default=0
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shops"
        verbose_name = "Магазин"
        verbose_name_plural = "Магазины"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class ShopSettings(models.Model):
    """Настройки магазина"""

    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name="settings")

    # Настройки заказов
    order_number_prefix = models.CharField(
        "Префикс номера заказа", max_length=5, default="ORD"
    )
    auto_order_numbering = models.BooleanField(
        "Автоматическая нумерация заказов", default=True
    )

    # Настройки уведомлений
    sms_notifications = models.BooleanField("SMS уведомления", default=False)
    email_notifications = models.BooleanField("Email уведомления", default=True)

    # Рабочее время
    work_hours_start = models.TimeField("Начало работы", null=True, blank=True)
    work_hours_end = models.TimeField("Конец работы", null=True, blank=True)
    work_days = models.CharField(
        "Рабочие дни",
        max_length=20,
        default="1,2,3,4,5",  # Пн-Пт
        help_text="Номера дней недели через запятую (1=Пн, 7=Вс)",
    )
    pos_barcode_enabled = models.BooleanField("POS с ШК включен", default=False)

    class Meta:
        db_table = "shop_settings"
        verbose_name = "Настройки магазина"
        verbose_name_plural = "Настройки магазинов"
