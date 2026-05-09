from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from finance.models import Payment
from orders.models import Order, OrderApproval, OrderService, RepairStage
from promotions.models import OrderDiscount

from .services import mark_order_for_sync


def _mark_after_commit(order: Order | None) -> None:
    if not order or not getattr(order, "id", None):
        return
    transaction.on_commit(lambda: mark_order_for_sync(order))


@receiver(post_save, sender=Order)
def mark_order_saved(sender, instance: Order, raw=False, **kwargs):
    if raw:
        return
    _mark_after_commit(instance)


@receiver(post_save, sender=RepairStage)
def mark_repair_stage_saved(sender, instance: RepairStage, raw=False, **kwargs):
    if raw:
        return
    _mark_after_commit(instance.order)


@receiver(post_delete, sender=RepairStage)
def mark_repair_stage_deleted(sender, instance: RepairStage, **kwargs):
    _mark_after_commit(instance.order)


@receiver(post_save, sender=OrderApproval)
def mark_order_approval_saved(sender, instance: OrderApproval, raw=False, **kwargs):
    if raw:
        return
    _mark_after_commit(instance.order)


@receiver(post_delete, sender=OrderApproval)
def mark_order_approval_deleted(sender, instance: OrderApproval, **kwargs):
    _mark_after_commit(instance.order)


@receiver(post_save, sender=OrderService)
def mark_order_service_saved(sender, instance: OrderService, raw=False, **kwargs):
    if raw:
        return
    _mark_after_commit(instance.order)


@receiver(post_delete, sender=OrderService)
def mark_order_service_deleted(sender, instance: OrderService, **kwargs):
    _mark_after_commit(instance.order)


@receiver(post_save, sender=OrderDiscount)
def mark_order_discount_saved(sender, instance: OrderDiscount, raw=False, **kwargs):
    if raw:
        return
    _mark_after_commit(instance.order)


@receiver(post_delete, sender=OrderDiscount)
def mark_order_discount_deleted(sender, instance: OrderDiscount, **kwargs):
    _mark_after_commit(instance.order)


@receiver(post_save, sender=Payment)
def mark_order_payment_saved(sender, instance: Payment, raw=False, **kwargs):
    if raw or not instance.order_id:
        return
    _mark_after_commit(instance.order)


@receiver(post_delete, sender=Payment)
def mark_order_payment_deleted(sender, instance: Payment, **kwargs):
    if not instance.order_id:
        return
    _mark_after_commit(instance.order)
