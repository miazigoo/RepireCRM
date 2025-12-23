from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from shops.models import Shop

from .models import InventoryItem, InventoryItemPriceHistory, StockBalance


@receiver(post_save, sender=InventoryItem)
def create_balances_for_all_shops(sender, instance: InventoryItem, created, **kwargs):
    if not created:
        return
    # Автосоздание нулевых остатков по всем активным магазинам
    for shop in Shop.objects.filter(is_active=True):
        StockBalance.objects.get_or_create(
            shop=shop,
            item=instance,
            defaults={
                "quantity": 0,
                "reserved_quantity": 0,
                "available_quantity": 0,
                "min_quantity": 5,
                "max_quantity": 50,
                "reorder_point": 10,
            },
        )
    # Начальные записи истории цен
    if instance.purchase_price is not None:
        InventoryItemPriceHistory.objects.create(
            item=instance,
            price_type=InventoryItemPriceHistory.PriceType.PURCHASE,
            value=instance.purchase_price,
            notes="Initial",
        )
    if instance.selling_price is not None:
        InventoryItemPriceHistory.objects.create(
            item=instance,
            price_type=InventoryItemPriceHistory.PriceType.SELLING,
            value=instance.selling_price,
            notes="Initial",
        )


@receiver(pre_save, sender=InventoryItem)
def log_price_changes(sender, instance: InventoryItem, **kwargs):
    if not instance.id:
        return
    try:
        old = sender.objects.get(id=instance.id)
    except sender.DoesNotExist:
        return
    # Изменение закупочной
    if old.purchase_price != instance.purchase_price:
        InventoryItemPriceHistory.objects.create(
            item=instance,
            price_type=InventoryItemPriceHistory.PriceType.PURCHASE,
            value=instance.purchase_price or Decimal("0"),
            notes="Manual change",
        )
    # Изменение продажной
    if old.selling_price != instance.selling_price:
        InventoryItemPriceHistory.objects.create(
            item=instance,
            price_type=InventoryItemPriceHistory.PriceType.SELLING,
            value=instance.selling_price or Decimal("0"),
            notes="Manual change",
        )
