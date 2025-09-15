# backend/API/loyalty/router.py
from ninja import Router
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404
from django.db.models import Q
from loyalty.models import (
    LoyaltyProgram, CustomerLoyalty, PointsTransaction,
    LoyaltyReward, CustomerReward
)
from loyalty.services import LoyaltyService
from customers.models import Customer
from orders.models import Order
from schemas.loyalty import (
    LoyaltyProgramSchema, CustomerLoyaltySchema, PointsTransactionSchema,
    LoyaltyRewardSchema, CustomerRewardSchema, RedeemPointsSchema
)

router = Router(tags=["Программа лояльности"])


@router.get("/programs", response=list[LoyaltyProgramSchema])
def list_loyalty_programs(request):
    """Получить список программ лояльности"""
    programs = LoyaltyProgram.objects.filter(is_active=True)
    if hasattr(request, 'current_shop') and request.current_shop:
        programs = programs.filter(
            Q(shops__isnull=True) | Q(shops=request.current_shop)
        ).distinct()
    return programs


@router.get("/customer/{customer_id}", response=CustomerLoyaltySchema)
def get_customer_loyalty(request, customer_id: int):
    """Получить информацию о программе лояльности клиента"""
    customer = get_object_or_404(Customer, id=customer_id)
    customer_loyalty = LoyaltyService.get_or_create_customer_loyalty(customer)

    if not customer_loyalty:
        return {"error": "Программа лояльности недоступна"}

    return customer_loyalty


@router.get("/customer/{customer_id}/transactions", response=list[PointsTransactionSchema])
@paginate
def get_customer_transactions(request, customer_id: int):
    """Получить историю транзакций баллов клиента"""
    customer = get_object_or_404(Customer, id=customer_id)
    customer_loyalty = CustomerLoyalty.objects.filter(customer=customer).first()

    if not customer_loyalty:
        return []

    return customer_loyalty.transactions.all()


@router.post("/redeem-points", response={200: dict, 400: dict})
def redeem_points(request, data: RedeemPointsSchema):
    """Списать баллы клиента"""
    try:
        customer = get_object_or_404(Customer, id=data.customer_id)
        order = get_object_or_404(Order, id=data.order_id)
        customer_loyalty = CustomerLoyalty.objects.filter(customer=customer).first()

        if not customer_loyalty:
            return 400, {"error": "Клиент не участвует в программе лояльности"}

        transaction_obj = LoyaltyService.redeem_points(
            customer_loyalty=customer_loyalty,
            points=data.points,
            order=order,
            description=data.description
        )

        # Рассчитываем размер скидки
        discount_amount = float(data.points * customer_loyalty.program.point_value)

        return {
            "success": True,
            "transaction_id": transaction_obj.id,
            "discount_amount": discount_amount,
            "remaining_points": customer_loyalty.available_points
        }

    except ValueError as e:
        return 400, {"error": str(e)}
    except Exception as e:
        return 400, {"error": "Ошибка при списании баллов"}


@router.post("/calculate-points/{order_id}", response=dict)
def calculate_points_for_order(request, order_id: int):
    """Рассчитать количество баллов за заказ"""
    order = get_object_or_404(Order, id=order_id)
    points = LoyaltyService.calculate_points_for_order(order)

    customer_loyalty = LoyaltyService.get_or_create_customer_loyalty(order.customer)
    tier_multiplier = customer_loyalty.get_tier_multiplier() if customer_loyalty else 1.0

    return {
        "points": points,
        "tier_level": customer_loyalty.tier_level if customer_loyalty else "bronze",
        "tier_multiplier": tier_multiplier,
        "order_amount": float(order.final_cost or order.cost_estimate)
    }


@router.get("/customer/{customer_id}/rewards", response=list[CustomerRewardSchema])
def get_customer_rewards(request, customer_id: int):
    """Получить награды клиента"""
    customer = get_object_or_404(Customer, id=customer_id)
    customer_loyalty = CustomerLoyalty.objects.filter(customer=customer).first()

    if not customer_loyalty:
        return []

    return customer_loyalty.rewards.select_related('reward').all()


@router.get("/rewards", response=list[LoyaltyRewardSchema])
def list_available_rewards(request):
    """Получить список доступных наград"""
    rewards = LoyaltyReward.objects.filter(is_active=True)
    return rewards


@router.post("/award-points/{order_id}", response={200: dict, 400: dict})
def award_points_for_order(request, order_id: int):
    """Начислить баллы за заказ"""
    try:
        order = get_object_or_404(Order, id=order_id)
        transaction_obj = LoyaltyService.award_points_for_order(order)

        if transaction_obj:
            return {
                "success": True,
                "points_awarded": transaction_obj.points,
                "transaction_id": transaction_obj.id
            }
        else:
            return 400, {"error": "Баллы не могут быть начислены"}

    except Exception as e:
        return 400, {"error": str(e)}
