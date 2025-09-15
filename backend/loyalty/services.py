# backend/loyalty/services.py
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from .models import (
    LoyaltyProgram, CustomerLoyalty, PointsTransaction,
    LoyaltyReward, CustomerReward
)
from orders.models import Order
from customers.models import Customer


class LoyaltyService:
    """Сервис для работы с программой лояльности"""

    @staticmethod
    def get_or_create_customer_loyalty(customer: Customer, program: LoyaltyProgram = None):
        """Получить или создать участие клиента в программе лояльности"""
        if not program:
            program = LoyaltyProgram.objects.filter(is_active=True).first()
            if not program:
                return None

        customer_loyalty, created = CustomerLoyalty.objects.get_or_create(
            customer=customer,
            program=program,
            defaults={
                'tier_level': CustomerLoyalty.TierLevel.BRONZE
            }
        )
        return customer_loyalty

    @staticmethod
    def calculate_points_for_order(order: Order) -> int:
        """Рассчитать количество баллов за заказ"""
        customer_loyalty = LoyaltyService.get_or_create_customer_loyalty(order.customer)
        if not customer_loyalty:
            return 0

        program = customer_loyalty.program
        order_amount = order.final_cost or order.cost_estimate

        # Проверяем минимальную сумму заказа
        if order_amount < program.min_order_amount:
            return 0

        # Базовые баллы
        base_points = int((order_amount * program.earn_rate / 100))

        # Множитель за уровень клиента
        tier_multiplier = customer_loyalty.get_tier_multiplier()

        total_points = int(base_points * tier_multiplier)
        return total_points

    @staticmethod
    @transaction.atomic
    def award_points_for_order(order: Order):
        """Начислить баллы за заказ"""
        if order.status != 'completed':
            return None

        # Проверяем, не начислялись ли уже баллы за этот заказ
        existing_transaction = PointsTransaction.objects.filter(
            order=order,
            transaction_type=PointsTransaction.TransactionType.EARNED
        ).first()

        if existing_transaction:
            return existing_transaction

        customer_loyalty = LoyaltyService.get_or_create_customer_loyalty(order.customer)
        if not customer_loyalty:
            return None

        points = LoyaltyService.calculate_points_for_order(order)
        if points <= 0:
            return None

        # Создаем транзакцию начисления
        transaction_obj = PointsTransaction.objects.create(
            customer_loyalty=customer_loyalty,
            transaction_type=PointsTransaction.TransactionType.EARNED,
            points=points,
            order=order,
            description=f"Начисление за заказ {order.order_number}",
            expires_at=LoyaltyService._calculate_expiry_date(customer_loyalty.program)
        )

        # Обновляем баланс клиента
        customer_loyalty.total_points += points
        customer_loyalty.available_points += points
        customer_loyalty.total_spent += (order.final_cost or order.cost_estimate)
        customer_loyalty.orders_count += 1

        # Обновляем уровень клиента
        new_tier = customer_loyalty.calculate_tier()
        if new_tier != customer_loyalty.tier_level:
            customer_loyalty.tier_level = new_tier
            # Можно добавить бонус за повышение уровня
            LoyaltyService._award_tier_bonus(customer_loyalty, new_tier)

        customer_loyalty.save()

        # Проверяем доступные награды
        LoyaltyService._check_and_award_rewards(customer_loyalty)

        return transaction_obj

    @staticmethod
    @transaction.atomic
    def redeem_points(customer_loyalty: CustomerLoyalty, points: int, order: Order, description: str = ""):
        """Списать баллы клиента"""
        if points > customer_loyalty.available_points:
            raise ValueError("Недостаточно баллов для списания")

        if points < customer_loyalty.program.min_redeem_points:
            raise ValueError(f"Минимум для списания: {customer_loyalty.program.min_redeem_points} баллов")

        # Проверяем максимальный процент оплаты баллами
        order_amount = order.final_cost or order.cost_estimate
        points_value = Decimal(points) * customer_loyalty.program.point_value
        max_redeem_amount = order_amount * customer_loyalty.program.max_redeem_percent / 100

        if points_value > max_redeem_amount:
            max_points = int(max_redeem_amount / customer_loyalty.program.point_value)
            raise ValueError(f"Максимум можно списать {max_points} баллов")

        # Создаем транзакцию списания
        transaction_obj = PointsTransaction.objects.create(
            customer_loyalty=customer_loyalty,
            transaction_type=PointsTransaction.TransactionType.REDEEMED,
            points=-points,
            order=order,
            description=description or f"Списание для заказа {order.order_number}"
        )

        # Обновляем баланс
        customer_loyalty.available_points -= points
        customer_loyalty.used_points += points
        customer_loyalty.save()

        return transaction_obj

    @staticmethod
    def _calculate_expiry_date(program: LoyaltyProgram):
        """Рассчитать дату истечения баллов"""
        if program.points_expire_days:
            return timezone.now() + timezone.timedelta(days=program.points_expire_days)
        return None

    @staticmethod
    def _award_tier_bonus(customer_loyalty: CustomerLoyalty, new_tier: str):
        """Начислить бонус за повышение уровня"""
        bonus_points = {
            CustomerLoyalty.TierLevel.SILVER: 500,
            CustomerLoyalty.TierLevel.GOLD: 1000,
            CustomerLoyalty.TierLevel.PLATINUM: 2000
        }

        points = bonus_points.get(new_tier, 0)
        if points > 0:
            PointsTransaction.objects.create(
                customer_loyalty=customer_loyalty,
                transaction_type=PointsTransaction.TransactionType.BONUS,
                points=points,
                description=f"Бонус за достижение уровня {customer_loyalty.get_tier_level_display()}"
            )

            customer_loyalty.total_points += points
            customer_loyalty.available_points += points

    @staticmethod
    def _check_and_award_rewards(customer_loyalty: CustomerLoyalty):
        """Проверить и выдать доступные награды"""
        available_rewards = LoyaltyReward.objects.filter(
            program=customer_loyalty.program,
            is_active=True,
            required_points__lte=customer_loyalty.total_points,
            required_orders_count__lte=customer_loyalty.orders_count
        )

        # Фильтруем по уровню если указан
        if customer_loyalty.tier_level:
            tier_hierarchy = {
                CustomerLoyalty.TierLevel.BRONZE: 1,
                CustomerLoyalty.TierLevel.SILVER: 2,
                CustomerLoyalty.TierLevel.GOLD: 3,
                CustomerLoyalty.TierLevel.PLATINUM: 4
            }
            current_tier_level = tier_hierarchy.get(customer_loyalty.tier_level, 1)

            available_rewards = available_rewards.filter(
                models.Q(required_tier='') |
                models.Q(required_tier__in=[
                    tier for tier, level in tier_hierarchy.items()
                    if level <= current_tier_level
                ])
            )

        # Проверяем временные ограничения
        now = timezone.now()
        available_rewards = available_rewards.filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=now),
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=now)
        )

        # Выдаем награды, которые клиент еще не получал
        for reward in available_rewards:
            existing_reward = CustomerReward.objects.filter(
                customer_loyalty=customer_loyalty,
                reward=reward
            ).first()

            if not existing_reward:
                CustomerReward.objects.create(
                    customer_loyalty=customer_loyalty,
                    reward=reward
                )

    @staticmethod
    def expire_points():
        """Списать просроченные баллы (для запуска по cron)"""
        expired_transactions = PointsTransaction.objects.filter(
            transaction_type=PointsTransaction.TransactionType.EARNED,
            expires_at__lt=timezone.now(),
            points__gt=0
        )

        for transaction_obj in expired_transactions:
            if transaction_obj.points > 0:
                # Создаем транзакцию списания просроченных баллов
                PointsTransaction.objects.create(
                    customer_loyalty=transaction_obj.customer_loyalty,
                    transaction_type=PointsTransaction.TransactionType.EXPIRED,
                    points=-transaction_obj.points,
                    description=f"Истечение срока действия баллов от {transaction_obj.created_at.date()}"
                )

                # Обновляем баланс
                customer_loyalty = transaction_obj.customer_loyalty
                customer_loyalty.available_points -= transaction_obj.points
                customer_loyalty.save()

                # Помечаем транзакцию как обработанную
                transaction_obj.points = 0
                transaction_obj.save()
