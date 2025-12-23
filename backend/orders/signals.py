from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from communications.services import communication_service
from loyalty.services import LoyaltyService
from notifications.services import notification_service

from .models import Order


@receiver(pre_save, sender=Order)
def notify_status_change(sender, instance: Order, **kwargs):
    if not instance.id:
        return
    old = sender.objects.get(id=instance.id)
    if old.status != instance.status:
        notification_service.notify_order_status_change(
            instance, old.status, instance.status, instance.created_by
        )


@receiver(post_save, sender=Order)
def post_order_saved(sender, instance: Order, created, **kwargs):
    # Начисление баллов при выдаче (completed)
    if instance.status == Order.StatusChoices.COMPLETED:
        tx = LoyaltyService.award_points_for_order(instance)
        if tx:
            notification_service.notify_loyalty_points_earned(
                instance.customer, tx.points, instance
            )

    # Внешние коммуникации при готовности к выдаче
    if instance.status == Order.StatusChoices.READY:
        communication_service.notify_ready(instance.customer, instance)

    # SLA вычисления при завершении
    if instance.status == Order.StatusChoices.COMPLETED:
        if instance.completed_at is None:
            # Подстрахуемся: если дата не выставлена (хотя выставляется в API), поставим сейчас
            instance.completed_at = timezone.now()

        if instance.estimated_completion:
            delta = instance.completed_at - instance.estimated_completion
            minutes = int(delta.total_seconds() // 60)
            on_time = minutes <= 0  # раньше или вовремя
            # Обновляем через update, чтобы не триггерить снова сигнал
            Order.objects.filter(pk=instance.pk).update(
                sla_on_time=on_time, sla_delay_minutes=minutes
            )
        else:
            Order.objects.filter(pk=instance.pk).update(
                sla_on_time=None, sla_delay_minutes=None
            )
