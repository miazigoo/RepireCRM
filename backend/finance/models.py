import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from sequences import get_next_value

from .fiscal_constants import (
    FiscalMeasure,
    FiscalPaymentMode,
    FiscalPaymentSubject,
    FiscalPaymentType,
    FiscalTaxationSystem,
    FiscalVatCode,
)

User = get_user_model()


class PaymentMethod(models.Model):
    """Способы оплаты"""

    name = models.CharField("Название", max_length=100, unique=True)
    code = models.CharField("Код", max_length=20, unique=True)
    description = models.TextField("Описание", blank=True)
    is_cash = models.BooleanField("Наличные", default=False)
    is_active = models.BooleanField("Активен", default=True)
    fiscal_payment_type = models.CharField(
        "Тип оплаты для фискального чека",
        max_length=20,
        choices=FiscalPaymentType.choices,
        default=FiscalPaymentType.ELECTRONIC,
        help_text="cash/electronic/prepaid/credit/other для ККМ и онлайн-чеков",
    )

    # Комиссии
    fee_percent = models.DecimalField(
        "Комиссия %", max_digits=5, decimal_places=2, default=Decimal("0")
    )
    fee_fixed = models.DecimalField(
        "Фиксированная комиссия", max_digits=10, decimal_places=2, default=Decimal("0")
    )

    class Meta:
        verbose_name = "Способ оплаты"
        verbose_name_plural = "Способы оплаты"

    def __str__(self):
        return self.name


class CashRegister(models.Model):
    """Кассы"""

    name = models.CharField("Название", max_length=100)
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, verbose_name="Магазин"
    )

    # Остаток денег
    cash_balance = models.DecimalField(
        "Остаток наличных", max_digits=15, decimal_places=2, default=Decimal("0")
    )

    # Ответственные
    cashiers = models.ManyToManyField(
        User, through="CashRegisterAccess", verbose_name="Кассиры"
    )

    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["shop", "name"]
        verbose_name = "Касса"
        verbose_name_plural = "Кассы"

    def __str__(self):
        return f"{self.shop.name} - {self.name}"


class CashRegisterAccess(models.Model):
    """Доступ к кассам"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cash_register = models.ForeignKey(CashRegister, on_delete=models.CASCADE)
    is_manager = models.BooleanField("Менеджер кассы", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "cash_register"]


class Payment(models.Model):
    """Платежи"""

    class PaymentType(models.TextChoices):
        INCOME = "income", "Приход"
        EXPENSE = "expense", "Расход"
        TRANSFER = "transfer", "Перевод"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "В обработке"
        COMPLETED = "completed", "Завершен"
        CANCELLED = "cancelled", "Отменен"
        FAILED = "failed", "Неуспешен"

    # Основная информация
    payment_number = models.CharField("Номер платежа", max_length=50, unique=True)
    payment_type = models.CharField(
        "Тип платежа", max_length=10, choices=PaymentType.choices
    )
    status = models.CharField(
        "Статус",
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    # Суммы
    amount = models.DecimalField(
        "Сумма", max_digits=15, decimal_places=2, validators=[MinValueValidator(0)]
    )
    fee_amount = models.DecimalField(
        "Размер комиссии", max_digits=15, decimal_places=2, default=Decimal("0")
    )
    net_amount = models.DecimalField(
        "Чистая сумма", max_digits=15, decimal_places=2, default=Decimal("0")
    )

    # Способ оплаты и касса
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    cash_register = models.ForeignKey(
        "CashRegister", on_delete=models.PROTECT, null=True, blank=True
    )

    # Связанные документы
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Заказ на ремонт",
    )
    purchase_order = models.ForeignKey(
        "inventory.PurchaseOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Заказ поставщику",
    )
    expense = models.ForeignKey(
        "Expense",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Расходная операция",
    )
    retail_sale = models.ForeignKey(
        "inventory.RetailSale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name="Розничная продажа",
    )

    # Фискализация
    fiscal_required = models.BooleanField("Требуется фискальный чек", default=True)
    fiscal_payment_mode = models.CharField(
        "Признак способа расчета",
        max_length=30,
        choices=FiscalPaymentMode.choices,
        default=FiscalPaymentMode.FULL_PAYMENT,
    )

    # Дополнительная информация
    description = models.TextField("Описание", blank=True)
    reference_number = models.CharField("Номер документа", max_length=100, blank=True)
    external_id = models.CharField("Внешний ID", max_length=100, blank=True)

    # Даты
    payment_date = models.DateTimeField("Дата платежа")
    processed_at = models.DateTimeField("Дата обработки", null=True, blank=True)

    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        ordering = ["-payment_date"]

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self._generate_payment_number()

        # Рассчитываем чистую сумму
        self.net_amount = self.amount - self.fee_amount

        super().save(*args, **kwargs)

    def _generate_payment_number(self) -> str:
        """
        Безгоночная генерация номера платежа.
        Глобальная последовательность: 'payment-number'
        Формат: PAY-00000001
        """
        seq = get_next_value("payment-number")
        return f"PAY-{seq:08d}"


class ExpenseCategory(models.Model):
    """Категории расходов"""

    name = models.CharField("Название", max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Родительская категория",
    )
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Категория расходов"
        verbose_name_plural = "Категории расходов"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name


class Expense(models.Model):
    """Расходные операции"""

    class ExpenseType(models.TextChoices):
        OPERATIONAL = "operational", "Операционные"
        ADMINISTRATIVE = "administrative", "Административные"
        MARKETING = "marketing", "Маркетинговые"
        EQUIPMENT = "equipment", "Оборудование"
        INVENTORY = "inventory", "Товары"
        SALARY = "salary", "Зарплата"
        RENT = "rent", "Аренда"
        UTILITIES = "utilities", "Коммунальные услуги"
        OTHER = "other", "Прочие"

    # Основная информация
    expense_number = models.CharField("Номер расхода", max_length=50, unique=True)
    title = models.CharField("Название", max_length=200)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    expense_type = models.CharField(
        "Тип расхода", max_length=20, choices=ExpenseType.choices
    )

    # Сумма
    amount = models.DecimalField(
        "Сумма", max_digits=15, decimal_places=2, validators=[MinValueValidator(0)]
    )

    # Связи
    shop = models.ForeignKey("shops.Shop", on_delete=models.PROTECT)
    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Поставщик/Подрядчик",
    )

    # Дополнительная информация
    description = models.TextField("Описание", blank=True)
    invoice_number = models.CharField("Номер счета", max_length=100, blank=True)
    receipt_file = models.FileField("Чек/Документ", upload_to="receipts/", blank=True)

    # Статус и даты
    is_approved = models.BooleanField("Утвержден", default=False)
    is_paid = models.BooleanField("Оплачен", default=False)
    expense_date = models.DateField("Дата расхода")

    # Утверждение и создание
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_expenses",
        verbose_name="Утвердил",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name="Создал"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Расход"
        verbose_name_plural = "Расходы"
        ordering = ["-expense_date"]

    def save(self, *args, **kwargs):
        if not self.expense_number:
            self.expense_number = self._generate_expense_number()
        super().save(*args, **kwargs)

    def _generate_expense_number(self) -> str:
        """
        Безгоночная генерация номера расхода.
        Последовательность на магазин: 'expense-{SHOPCODE}'
        Формат: EXP-{SHOP}-{seq:06d}
        """
        # shop обязателен для Expense, поэтому sequence можно завязать на филиал
        seq = get_next_value(f"expense-{self.shop.code}")
        return f"EXP-{self.shop.code}-{seq:06d}"


class FinancialReport(models.Model):
    """Финансовые отчеты"""

    class ReportPeriod(models.TextChoices):
        DAY = "day", "День"
        WEEK = "week", "Неделя"
        MONTH = "month", "Месяц"
        QUARTER = "quarter", "Квартал"
        YEAR = "year", "Год"
        CUSTOM = "custom", "Произвольный период"

    name = models.CharField("Название", max_length=200)
    period = models.CharField("Период", max_length=10, choices=ReportPeriod.choices)
    date_from = models.DateField("С даты")
    date_to = models.DateField("По дату")

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Магазин",
    )

    # Данные отчета
    total_income = models.DecimalField(
        "Общий доход", max_digits=15, decimal_places=2, default=Decimal("0")
    )
    total_expenses = models.DecimalField(
        "Общие расходы", max_digits=15, decimal_places=2, default=Decimal("0")
    )
    net_profit = models.DecimalField(
        "Чистая прибыль", max_digits=15, decimal_places=2, default=Decimal("0")
    )

    # Детализация
    report_data = models.JSONField("Данные отчета", default=dict)

    # Метаданные
    generated_by = models.ForeignKey(User, on_delete=models.PROTECT)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Финансовый отчет"
        verbose_name_plural = "Финансовые отчеты"
        ordering = ["-generated_at"]


class OnlinePayment(models.Model):
    """Онлайн-платеж через внешний платежный шлюз."""

    class Provider(models.TextChoices):
        YOOKASSA = "yookassa", "ЮKassa"

    class Purpose(models.TextChoices):
        ORDER = "order", "Оплата заказа"
        SUBSCRIPTION = "subscription", "Оплата подписки"

    class PaymentMethodType(models.TextChoices):
        ANY = "any", "Платежная форма"
        BANK_CARD = "bank_card", "Банковская карта"
        SBP = "sbp", "СБП"
        YOO_MONEY = "yoo_money", "ЮMoney"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает оплаты"
        WAITING_FOR_CAPTURE = "waiting_for_capture", "Ожидает подтверждения"
        SUCCEEDED = "succeeded", "Оплачен"
        CANCELED = "canceled", "Отменен"
        FAILED = "failed", "Ошибка"

    provider = models.CharField(
        "Провайдер",
        max_length=20,
        choices=Provider.choices,
        default=Provider.YOOKASSA,
    )
    purpose = models.CharField("Назначение", max_length=20, choices=Purpose.choices)
    status = models.CharField(
        "Статус",
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    payment_method_type = models.CharField(
        "Тип способа оплаты",
        max_length=30,
        choices=PaymentMethodType.choices,
        default=PaymentMethodType.BANK_CARD,
    )

    amount = models.DecimalField(
        "Сумма", max_digits=15, decimal_places=2, validators=[MinValueValidator(0)]
    )
    currency = models.CharField("Валюта", max_length=3, default="RUB")
    description = models.CharField("Описание", max_length=255)

    provider_payment_id = models.CharField(
        "ID платежа у провайдера", max_length=120, blank=True, db_index=True
    )
    idempotence_key = models.UUIDField(
        "Ключ идемпотентности", default=uuid.uuid4, unique=True
    )
    confirmation_url = models.URLField("Ссылка на оплату", max_length=1000, blank=True)
    return_url = models.URLField("Ссылка возврата", max_length=1000, blank=True)
    test_token = models.UUIDField("Токен тестовой оплаты", default=uuid.uuid4)
    raw_payload = models.JSONField("Данные провайдера", default=dict, blank=True)
    fiscal_receipt_snapshot = models.JSONField(
        "Снимок фискального чека", default=dict, blank=True
    )
    fiscal_receipt_error = models.TextField("Ошибка подготовки чека", blank=True)

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="online_payments",
        verbose_name="Заказ",
    )
    organization = models.ForeignKey(
        "shops.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="online_payments",
        verbose_name="Организация",
    )
    subscription_plan = models.ForeignKey(
        "shops.SubscriptionPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="online_payments",
        verbose_name="Тариф подписки",
    )
    local_payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="online_payment",
        verbose_name="Локальный платеж",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="online_payments",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField("Дата оплаты", null=True, blank=True)

    class Meta:
        verbose_name = "Онлайн-платеж"
        verbose_name_plural = "Онлайн-платежи"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["purpose", "status"]),
            models.Index(fields=["provider", "provider_payment_id"]),
        ]

    def __str__(self):
        return f"{self.get_purpose_display()} {self.amount} {self.currency}"


class PaymentReceipt(models.Model):
    """Фискальный чек, подготовленный для ККМ или онлайн-кассы провайдера."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        QUEUED = "queued", "В очереди"
        SENT = "sent", "Отправлен"
        REGISTERED = "registered", "Зарегистрирован"
        FAILED = "failed", "Ошибка"
        NOT_REQUIRED = "not_required", "Не требуется"

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="fiscal_receipt",
        verbose_name="Платеж",
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    provider = models.CharField("Провайдер ККМ", max_length=30, blank=True)
    provider_receipt_id = models.CharField(
        "ID чека у провайдера", max_length=120, blank=True, db_index=True
    )
    taxation_system = models.CharField(
        "Система налогообложения",
        max_length=30,
        choices=FiscalTaxationSystem.choices,
        default=FiscalTaxationSystem.USN_INCOME,
    )
    payment_type = models.CharField(
        "Тип оплаты",
        max_length=20,
        choices=FiscalPaymentType.choices,
        default=FiscalPaymentType.ELECTRONIC,
    )
    total_amount = models.DecimalField("Сумма чека", max_digits=15, decimal_places=2)
    received_amount = models.DecimalField(
        "Получено текущим платежом",
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
    )
    currency = models.CharField("Валюта", max_length=3, default="RUB")
    customer_email = models.EmailField("Email покупателя", blank=True)
    customer_phone = models.CharField("Телефон покупателя", max_length=30, blank=True)
    normalized_snapshot = models.JSONField(
        "Нормализованный чек", default=dict, blank=True
    )
    provider_payload = models.JSONField("Payload провайдера", default=dict, blank=True)
    provider_response = models.JSONField("Ответ провайдера", default=dict, blank=True)
    error_message = models.TextField("Ошибка", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField("Дата отправки", null=True, blank=True)
    registered_at = models.DateTimeField("Дата регистрации", null=True, blank=True)

    class Meta:
        verbose_name = "Фискальный чек"
        verbose_name_plural = "Фискальные чеки"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["provider", "provider_receipt_id"]),
        ]

    def __str__(self):
        return f"{self.payment.payment_number}: {self.total_amount} {self.currency}"


class PaymentReceiptItem(models.Model):
    """Позиция фискального чека."""

    receipt = models.ForeignKey(
        PaymentReceipt, on_delete=models.CASCADE, related_name="items"
    )
    position = models.PositiveIntegerField("Позиция")
    source_type = models.CharField("Источник", max_length=40, blank=True)
    source_id = models.PositiveIntegerField("ID источника", null=True, blank=True)
    name = models.CharField("Наименование", max_length=128)
    quantity = models.DecimalField("Количество", max_digits=12, decimal_places=3)
    unit_price = models.DecimalField("Цена", max_digits=15, decimal_places=2)
    amount = models.DecimalField("Сумма", max_digits=15, decimal_places=2)
    vat_code = models.CharField(
        "НДС", max_length=20, choices=FiscalVatCode.choices, default=FiscalVatCode.NONE
    )
    payment_subject = models.CharField(
        "Признак предмета расчета",
        max_length=30,
        choices=FiscalPaymentSubject.choices,
        default=FiscalPaymentSubject.SERVICE,
    )
    payment_mode = models.CharField(
        "Признак способа расчета",
        max_length=30,
        choices=FiscalPaymentMode.choices,
        default=FiscalPaymentMode.FULL_PAYMENT,
    )
    measure = models.CharField(
        "Единица измерения",
        max_length=30,
        choices=FiscalMeasure.choices,
        default=FiscalMeasure.PIECE,
    )
    sku = models.CharField("Артикул", max_length=100, blank=True)
    barcode = models.CharField("Штрихкод", max_length=50, blank=True)
    metadata = models.JSONField("Метаданные", default=dict, blank=True)

    class Meta:
        verbose_name = "Позиция фискального чека"
        verbose_name_plural = "Позиции фискальных чеков"
        ordering = ["position"]
        unique_together = ["receipt", "position"]
