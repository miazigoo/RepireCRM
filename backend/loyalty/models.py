# backend/loyalty/models.py
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from customers.models import Customer
from orders.models import Order
from shops.models import Shop


class LoyaltyProgram(models.Model):
    """Программа лояльности"""

    class ProgramType(models.TextChoices):
        POINTS = 'points', 'Бонусные баллы'
        CASHBACK = 'cashback', 'Кэшбэк'
        DISCOUNT = 'discount', 'Скидочная программа'

    name = models.CharField("Название программы", max_length=100)
    program_type = models.CharField(
        "Тип программы",
        max_length=20,
        choices=ProgramType.choices,
        default=ProgramType.POINTS
    )
    description = models.TextField("Описание", blank=True)

    # Настройки начисления
    earn_rate = models.DecimalField(
        "Процент начисления",
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.0'),
        help_text="Процент от суммы заказа"
    )
    min_order_amount = models.DecimalField(
        "Минимальная сумма заказа",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Настройки использования
    min_redeem_points = models.PositiveIntegerField(
        "Минимум баллов для списания",
        default=100
    )
    max_redeem_percent = models.DecimalField(
        "Максимальный процент оплаты баллами",
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.0'),
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    point_value = models.DecimalField(
        "Стоимость одного балла (в рублях)",
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00')
    )

    # Срок действия баллов
    points_expire_days = models.PositiveIntegerField(
        "Срок действия баллов (дни)",
        default=365,
        null=True,
        blank=True,
        help_text="Оставьте пустым для бессрочных баллов"
    )

    # Активность программы
    is_active = models.BooleanField("Активна", default=True)
    shops = models.ManyToManyField(
        Shop,
        verbose_name="Доступна в магазинах",
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loyalty_programs'
        verbose_name = 'Программа лояльности'
        verbose_name_plural = 'Программы лояльности'

    def __str__(self):
        return self.name


class CustomerLoyalty(models.Model):
    """Участие клиента в программе лояльности"""

    class TierLevel(models.TextChoices):
        BRONZE = 'bronze', 'Бронзовый'
        SILVER = 'silver', 'Серебряный'
        GOLD = 'gold', 'Золотой'
        PLATINUM = 'platinum', 'Платиновый'

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='loyalty'
    )
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE
    )

    # Баллы и статус
    total_points = models.PositiveIntegerField("Всего баллов", default=0)
    available_points = models.PositiveIntegerField("Доступно баллов", default=0)
    used_points = models.PositiveIntegerField("Использовано баллов", default=0)

    # Уровень клиента
    tier_level = models.CharField(
        "Уровень",
        max_length=20,
        choices=TierLevel.choices,
        default=TierLevel.BRONZE
    )
    tier_points_threshold = models.PositiveIntegerField(
        "Баллы для следующего уровня",
        default=1000
    )

    # Статистика
    total_spent = models.DecimalField(
        "Общая сумма покупок",
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    orders_count = models.PositiveIntegerField("Количество заказов", default=0)

    # Даты
    joined_at = models.DateTimeField("Дата вступления", auto_now_add=True)
    last_activity = models.DateTimeField("Последняя активность", auto_now=True)

    class Meta:
        db_table = 'customer_loyalty'
        verbose_name = 'Участие в программе лояльности'
        verbose_name_plural = 'Участие в программах лояльности'
        unique_together = ['customer', 'program']

    def __str__(self):
        return f"{self.customer.full_name} - {self.program.name}"

    def calculate_tier(self):
        """Расчет уровня клиента на основе потраченной суммы"""
        if self.total_spent >= 100000:
            return self.TierLevel.PLATINUM
        elif self.total_spent >= 50000:
            return self.TierLevel.GOLD
        elif self.total_spent >= 20000:
            return self.TierLevel.SILVER
        else:
            return self.TierLevel.BRONZE

    def get_tier_multiplier(self):
        """Получить множитель начисления для текущего уровня"""
        multipliers = {
            self.TierLevel.BRONZE: 1.0,
            self.TierLevel.SILVER: 1.2,
            self.TierLevel.GOLD: 1.5,
            self.TierLevel.PLATINUM: 2.0
        }
        return multipliers.get(self.tier_level, 1.0)


class PointsTransaction(models.Model):
    """Транзакции с баллами"""

    class TransactionType(models.TextChoices):
        EARNED = 'earned', 'Начислено'
        REDEEMED = 'redeemed', 'Списано'
        EXPIRED = 'expired', 'Сгорели'
        BONUS = 'bonus', 'Бонус'
        REFUND = 'refund', 'Возврат'

    customer_loyalty = models.ForeignKey(
        CustomerLoyalty,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        "Тип транзакции",
        max_length=20,
        choices=TransactionType.choices
    )
    points = models.IntegerField("Количество баллов")
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loyalty_transactions'
    )

    description = models.CharField("Описание", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField("Срок действия", null=True, blank=True)

    class Meta:
        db_table = 'points_transactions'
        verbose_name = 'Транзакция баллов'
        verbose_name_plural = 'Транзакции баллов'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_loyalty.customer.full_name} - {self.points} баллов ({self.get_transaction_type_display()})"


class LoyaltyReward(models.Model):
    """Награды программы лояльности"""

    class RewardType(models.TextChoices):
        DISCOUNT = 'discount', 'Скидка'
        FREE_SERVICE = 'free_service', 'Бесплатная услуга'
        GIFT = 'gift', 'Подарок'
        POINTS_BONUS = 'points_bonus', 'Бонусные баллы'

    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='rewards'
    )
    name = models.CharField("Название награды", max_length=100)
    reward_type = models.CharField(
        "Тип награды",
        max_length=20,
        choices=RewardType.choices
    )
    description = models.TextField("Описание")

    # Условия получения
    required_points = models.PositiveIntegerField("Необходимо баллов", default=0)
    required_tier = models.CharField(
        "Необходимый уровень",
        max_length=20,
        choices=CustomerLoyalty.TierLevel.choices,
        blank=True
    )
    required_orders_count = models.PositiveIntegerField(
        "Необходимо заказов",
        default=0
    )

    # Параметры награды
    discount_percent = models.DecimalField(
        "Размер скидки (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    bonus_points = models.PositiveIntegerField(
        "Бонусные баллы",
        null=True,
        blank=True
    )

    # Ограничения
    is_active = models.BooleanField("Активна", default=True)
    valid_from = models.DateTimeField("Действует с", null=True, blank=True)
    valid_to = models.DateTimeField("Действует до", null=True, blank=True)
    usage_limit = models.PositiveIntegerField(
        "Лимит использований",
        null=True,
        blank=True,
        help_text="Оставьте пустым для безлимитного использования"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loyalty_rewards'
        verbose_name = 'Награда программы лояльности'
        verbose_name_plural = 'Награды программы лояльности'

    def __str__(self):
        return f"{self.program.name} - {self.name}"


class CustomerReward(models.Model):
    """Полученные клиентом награды"""
    customer_loyalty = models.ForeignKey(
        CustomerLoyalty,
        on_delete=models.CASCADE,
        related_name='rewards'
    )
    reward = models.ForeignKey(
        LoyaltyReward,
        on_delete=models.CASCADE
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Заказ, при котором была получена награда"
    )

    received_at = models.DateTimeField("Дата получения", auto_now_add=True)
    used_at = models.DateTimeField("Дата использования", null=True, blank=True)
    is_used = models.BooleanField("Использована", default=False)

    class Meta:
        db_table = 'customer_rewards'
        verbose_name = 'Награда клиента'
        verbose_name_plural = 'Награды клиентов'
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.customer_loyalty.customer.full_name} - {self.reward.name}"
