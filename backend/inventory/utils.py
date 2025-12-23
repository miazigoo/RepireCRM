from typing import Optional

from .models import InventoryItem, InventoryItemBarcode


def find_item_by_barcode(barcode: str) -> Optional[InventoryItem]:
    ib = (
        InventoryItemBarcode.objects.select_related("item")
        .filter(barcode=barcode, item__is_active=True)
        .first()
    )
    return ib.item if ib else None
