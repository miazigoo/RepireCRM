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

    class Meta:
        db_table = "shop_settings"
        verbose_name = "Настройки магазина"
        verbose_name_plural = "Настройки магазинов"
