from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

MONEY = Decimal("0.01")


class Promotion(models.Model):
    """Акция или скидочное правило, доступное в одном или нескольких филиалах."""

    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Процент"
        FIXED = "fixed", "Фиксированная сумма"

    name = models.CharField("Название", max_length=160)
    description = models.TextField("Описание", blank=True)
    discount_type = models.CharField(
        "Тип скидки",
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENT,
    )
    value = models.DecimalField(
        "Размер скидки",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    max_discount_amount = models.DecimalField(
        "Максимальная скидка",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    min_order_amount = models.DecimalField(
        "Минимальная сумма заказа",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    starts_at = models.DateTimeField("Действует с", null=True, blank=True)
    ends_at = models.DateTimeField("Действует до", null=True, blank=True)
    is_active = models.BooleanField("Активна", default=True)
    auto_apply = models.BooleanField("Применять автоматически", default=False)
    stackable = models.BooleanField("Можно сочетать с другими скидками", default=False)
    usage_limit = models.PositiveIntegerField(
        "Общий лимит применений", null=True, blank=True
    )
    per_customer_limit = models.PositiveIntegerField(
        "Лимит на клиента", null=True, blank=True
    )
    shops = models.ManyToManyField(
        "shops.Shop",
        verbose_name="Филиалы",
        blank=True,
        help_text="Если филиалы не выбраны, акция доступна во всех филиалах.",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_promotions",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "promotions"
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ["-is_active", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "auto_apply"]),
            models.Index(fields=["starts_at", "ends_at"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_current(self) -> bool:
        now = timezone.now()
        return bool(
            self.is_active
            and (self.starts_at is None or self.starts_at <= now)
            and (self.ends_at is None or self.ends_at >= now)
        )

    @property
    def used_count(self) -> int:
        return self.order_discounts.count()

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        subtotal = Decimal(str(subtotal or 0))
        if subtotal <= 0 or subtotal < self.min_order_amount:
            return Decimal("0.00")
        if self.discount_type == self.DiscountType.PERCENT:
            amount = subtotal * self.value / Decimal("100")
        else:
            amount = self.value
        if self.max_discount_amount is not None:
            amount = min(amount, self.max_discount_amount)
        amount = min(amount, subtotal)
        return amount.quantize(MONEY, rounding=ROUND_HALF_UP)


class PromoCode(models.Model):
    """Промокод, который применяет связанную акцию к заказу."""

    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="codes",
        verbose_name="Акция",
    )
    code = models.CharField("Промокод", max_length=40, unique=True)
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    starts_at = models.DateTimeField("Действует с", null=True, blank=True)
    ends_at = models.DateTimeField("Действует до", null=True, blank=True)
    usage_limit = models.PositiveIntegerField("Общий лимит", null=True, blank=True)
    per_customer_limit = models.PositiveIntegerField(
        "Лимит на клиента", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "promo_codes"
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["is_active", "code"]),
            models.Index(fields=["starts_at", "ends_at"]),
        ]

    def __str__(self):
        return self.code

    @property
    def is_current(self) -> bool:
        now = timezone.now()
        return bool(
            self.is_active
            and self.promotion.is_current
            and (self.starts_at is None or self.starts_at <= now)
            and (self.ends_at is None or self.ends_at >= now)
        )

    @property
    def used_count(self) -> int:
        return self.redemptions.count()

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class OrderDiscount(models.Model):
    """Фактически примененная скидка в заказе."""

    class Source(models.TextChoices):
        MANUAL = "manual", "Ручная скидка"
        PROMO_CODE = "promo_code", "Промокод"
        AUTO = "auto", "Автоматическая акция"
        LOYALTY = "loyalty", "Лояльность"

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="discounts",
        verbose_name="Заказ",
    )
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_discounts",
        verbose_name="Акция",
    )
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redemptions",
        verbose_name="Промокод",
    )
    source = models.CharField(
        "Источник",
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    label = models.CharField("Название скидки", max_length=160)
    amount = models.DecimalField(
        "Сумма скидки",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_order_discounts",
        verbose_name="Кто применил",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_discounts"
        verbose_name = "Скидка заказа"
        verbose_name_plural = "Скидки заказов"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "source"]),
            models.Index(fields=["promotion"]),
            models.Index(fields=["promo_code"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "promo_code"],
                condition=Q(promo_code__isnull=False),
                name="uniq_order_promo_code_discount",
            )
        ]

    def __str__(self):
        return f"{self.order_id}: {self.label} - {self.amount}"
