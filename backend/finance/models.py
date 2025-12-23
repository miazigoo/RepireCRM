from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from sequences import get_next_value

User = get_user_model()


class PaymentMethod(models.Model):
    """Способы оплаты"""

    name = models.CharField("Название", max_length=100, unique=True)
    code = models.CharField("Код", max_length=20, unique=True)
    description = models.TextField("Описание", blank=True)
    is_cash = models.BooleanField("Наличные", default=False)
    is_active = models.BooleanField("Активен", default=True)

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
