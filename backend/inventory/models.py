from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from sequences import get_next_value

User = get_user_model()


class Category(models.Model):
    """Категории товаров"""

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
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name


class Supplier(models.Model):
    """Поставщики"""

    name = models.CharField("Название", max_length=200)
    contact_person = models.CharField("Контактное лицо", max_length=100, blank=True)
    email = models.EmailField("Email", blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    address = models.TextField("Адрес", blank=True)

    # Условия сотрудничества
    payment_terms = models.CharField("Условия оплаты", max_length=200, blank=True)
    delivery_terms = models.CharField("Условия доставки", max_length=200, blank=True)
    min_order_amount = models.DecimalField(
        "Минимальная сумма заказа",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
    )

    # Рейтинг и статистика
    rating = models.DecimalField(
        "Рейтинг",
        max_digits=3,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )
    total_orders = models.PositiveIntegerField("Всего заказов", default=0)
    total_amount = models.DecimalField(
        "Общая сумма заказов", max_digits=15, decimal_places=2, default=Decimal("0")
    )

    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ["name"]

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """Номенклатура товаров"""

    class ItemType(models.TextChoices):
        COMPONENT = "component", "Комплектующие"
        ACCESSORY = "accessory", "Аксессуары"
        CONSUMABLE = "consumable", "Расходные материалы"
        TOOL = "tool", "Инструменты"
        SOFTWARE = "software", "Программное обеспечение"
        SERVICE = "service", "Услуга"

    # Основная информация
    name = models.CharField("Название", max_length=200)
    sku = models.CharField("Артикул", max_length=100, unique=True)
    barcode = models.CharField("Штрихкод", max_length=50, blank=True)
    item_type = models.CharField("Тип", max_length=20, choices=ItemType.choices)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, verbose_name="Категория"
    )

    description = models.TextField("Описание", blank=True)
    specifications = models.JSONField(
        "Технические характеристики", default=dict, blank=True
    )

    # Совместимость
    compatible_models = models.ManyToManyField(
        "device.DeviceModel", blank=True, verbose_name="Совместимые модели"
    )

    # Цены
    purchase_price = models.DecimalField(
        "Закупочная цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    selling_price = models.DecimalField(
        "Продажная цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    markup_percent = models.DecimalField(
        "Наценка %", max_digits=5, decimal_places=2, default=Decimal("0")
    )

    # Единицы измерения
    unit = models.CharField("Единица измерения", max_length=20, default="шт")
    weight = models.DecimalField(
        "Вес (кг)", max_digits=8, decimal_places=3, null=True, blank=True
    )

    # Поставщики
    primary_supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_items",
        verbose_name="Основной поставщик",
    )
    suppliers = models.ManyToManyField(
        Supplier, through="SupplierItem", blank=True, verbose_name="Поставщики"
    )

    # Настройки учета
    track_quantity = models.BooleanField("Вести количественный учет", default=True)
    allow_negative_stock = models.BooleanField(
        "Разрешить отрицательные остатки", default=False
    )

    # Метаданные
    is_active = models.BooleanField("Активен", default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def total_stock(self):
        """Общий остаток по всем магазинам"""
        return self.stock_balances.aggregate(total=models.Sum("quantity"))["total"] or 0


class SupplierItem(models.Model):
    """Связь товара с поставщиком"""

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)

    supplier_sku = models.CharField("Артикул поставщика", max_length=100, blank=True)
    supplier_price = models.DecimalField(
        "Цена поставщика", max_digits=10, decimal_places=2
    )
    min_order_qty = models.PositiveIntegerField(
        "Минимальное количество заказа", default=1
    )
    delivery_days = models.PositiveIntegerField("Срок поставки (дни)", default=7)

    is_preferred = models.BooleanField("Предпочтительный", default=False)
    last_order_date = models.DateTimeField("Последний заказ", null=True, blank=True)

    class Meta:
        unique_together = ["supplier", "item"]


class StockBalance(models.Model):
    """Остатки товаров по магазинам"""

    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, verbose_name="Магазин"
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="stock_balances",
        verbose_name="Товар",
    )

    # Количество
    quantity = models.IntegerField("Количество", default=0)
    reserved_quantity = models.PositiveIntegerField("Зарезервировано", default=0)
    available_quantity = models.IntegerField("Доступно", default=0)

    # Пороговые значения
    min_quantity = models.PositiveIntegerField("Минимальный остаток", default=5)
    max_quantity = models.PositiveIntegerField("Максимальный остаток", default=50)
    reorder_point = models.PositiveIntegerField("Точка перезаказа", default=10)

    # Размещение
    location = models.CharField("Место хранения", max_length=100, blank=True)
    shelf = models.CharField("Полка", max_length=50, blank=True)

    # Метаданные
    last_movement_date = models.DateTimeField("Последнее движение", auto_now=True)
    last_inventory_date = models.DateTimeField(
        "Последняя инвентаризация", null=True, blank=True
    )

    class Meta:
        unique_together = ["shop", "item"]
        verbose_name = "Остаток товара"
        verbose_name_plural = "Остатки товаров"

    def save(self, *args, **kwargs):
        self.available_quantity = self.quantity - self.reserved_quantity
        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return self.available_quantity <= self.min_quantity

    @property
    def needs_reorder(self):
        return self.available_quantity <= self.reorder_point


class StockMovement(models.Model):
    """Движения товаров"""

    class MovementType(models.TextChoices):
        RECEIPT = "receipt", "Приход"
        SHIPMENT = "shipment", "Расход"
        TRANSFER = "transfer", "Перемещение"
        ADJUSTMENT = "adjustment", "Корректировка"
        RESERVATION = "reservation", "Резервирование"
        UNRESERVATION = "unreservation", "Снятие резерва"
        INVENTORY = "inventory", "Инвентаризация"
        WRITE_OFF = "write_off", "Списание"
        RETURN = "return", "Возврат"

    # Основная информация
    stock_balance = models.ForeignKey(
        StockBalance, on_delete=models.CASCADE, related_name="movements"
    )
    movement_type = models.CharField(
        "Тип движения", max_length=20, choices=MovementType.choices
    )

    # Количества
    quantity_before = models.IntegerField("Количество до")
    quantity_change = models.IntegerField("Изменение количества")
    quantity_after = models.IntegerField("Количество после")

    # Связанные документы
    purchase_order = models.ForeignKey(
        "PurchaseOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Заказ поставщику",
    )
    repair_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Заказ на ремонт",
    )

    # Дополнительная информация
    reference_number = models.CharField("Номер документа", max_length=100, blank=True)
    notes = models.TextField("Комментарий", blank=True)
    cost_per_unit = models.DecimalField(
        "Себестоимость за единицу",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Движение товара"
        verbose_name_plural = "Движения товаров"
        ordering = ["-created_at"]


class PurchaseOrder(models.Model):
    """Заказы поставщикам"""

    class OrderStatus(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SENT = "sent", "Отправлен"
        CONFIRMED = "confirmed", "Подтвержден"
        PARTIALLY_RECEIVED = "partially_received", "Частично получен"
        RECEIVED = "received", "Получен"
        CANCELLED = "cancelled", "Отменен"

    # Основная информация
    order_number = models.CharField("Номер заказа", max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, verbose_name="Поставщик"
    )
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.PROTECT, verbose_name="Магазин"
    )

    status = models.CharField(
        "Статус", max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT
    )

    # Даты
    order_date = models.DateTimeField("Дата заказа", auto_now_add=True)
    expected_delivery_date = models.DateTimeField(
        "Ожидаемая дата доставки", null=True, blank=True
    )
    actual_delivery_date = models.DateTimeField(
        "Фактическая дата доставки", null=True, blank=True
    )

    # Суммы
    subtotal = models.DecimalField(
        "Подитог", max_digits=15, decimal_places=2, default=Decimal("0")
    )
    tax_amount = models.DecimalField(
        "Сумма налога", max_digits=15, decimal_places=2, default=Decimal("0")
    )
    total_amount = models.DecimalField(
        "Общая сумма", max_digits=15, decimal_places=2, default=Decimal("0")
    )

    # Дополнительная информация
    notes = models.TextField("Комментарии", blank=True)
    terms_and_conditions = models.TextField("Условия", blank=True)

    # Метаданные
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name="Создал"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_purchase_orders",
        verbose_name="Утвердил",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заказ поставщику"
        verbose_name_plural = "Заказы поставщикам"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        from django.db.models import Max

        last_order = PurchaseOrder.objects.aggregate(Max("id"))["id__max"] or 0
        return f"PO-{self.shop.code}-{last_order + 1:06d}"


class PurchaseOrderItem(models.Model):
    """Позиции в заказе поставщику"""

    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)

    # Количества
    ordered_quantity = models.PositiveIntegerField("Заказано")
    received_quantity = models.PositiveIntegerField("Получено", default=0)

    # Цены
    unit_price = models.DecimalField("Цена за единицу", max_digits=10, decimal_places=2)
    total_price = models.DecimalField(
        "Общая стоимость", max_digits=15, decimal_places=2
    )

    # Дополнительно
    supplier_sku = models.CharField("Артикул поставщика", max_length=100, blank=True)
    notes = models.TextField("Комментарии", blank=True)

    class Meta:
        unique_together = ["purchase_order", "item"]

    def save(self, *args, **kwargs):
        self.total_price = self.ordered_quantity * self.unit_price
        super().save(*args, **kwargs)


class RetailSale(models.Model):
    """Розничная продажа в магазине (через скан ШК или вручную)"""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        COMPLETED = "completed", "Завершена"
        CANCELLED = "cancelled", "Отменена"

    sale_number = models.CharField("Номер продажи", max_length=50, unique=True)
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.PROTECT, verbose_name="Магазин"
    )
    cashier = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Кассир")
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.SET_NULL, null=True, blank=True
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    subtotal = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0")
    )
    discount_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0")
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0")
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Розничная продажа"
        verbose_name_plural = "Розничные продажи"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.sale_number:
            seq = get_next_value(f"sale-{self.shop.code}")
            self.sale_number = f"SAL-{self.shop.code}-{seq:06d}"
        self.total_amount = (self.subtotal or 0) - (self.discount_amount or 0)
        super().save(*args, **kwargs)


class RetailSaleItem(models.Model):
    sale = models.ForeignKey(RetailSale, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        verbose_name = "Позиция продажи"
        verbose_name_plural = "Позиции продажи"
        unique_together = ["sale", "item"]

    def save(self, *args, **kwargs):
        self.total_price = (self.unit_price or 0) * (self.quantity or 0)
        super().save(*args, **kwargs)


class BarcodeScanEvent(models.Model):
    """Лог события сканирования для аудита и аналитики"""

    class ScanContext(models.TextChoices):
        POS = "pos", "Продажа (POS)"
        INVENTORY = "inventory", "Склад"

    barcode = models.CharField("Штрихкод", max_length=50)
    item = models.ForeignKey(
        InventoryItem, on_delete=models.SET_NULL, null=True, blank=True
    )
    shop = models.ForeignKey("shops.Shop", on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    context = models.CharField(max_length=20, choices=ScanContext.choices)
    quantity = models.IntegerField("Количество", default=1)

    notes = models.TextField("Примечания", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Скан ШК"
        verbose_name_plural = "Сканы ШК"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["barcode"]),
            models.Index(fields=["shop", "context"]),
        ]


class InventoryItemBarcode(models.Model):
    """Доп. штрихкоды товара (разные поставщики/партии)"""

    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="barcodes"
    )
    barcode = models.CharField("Штрихкод", max_length=50)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ШК товара"
        verbose_name_plural = "ШК товаров"
        unique_together = ["item", "barcode"]
        indexes = [models.Index(fields=["barcode"])]

    def __str__(self):
        return f"{self.item.sku} [{self.barcode}]"


class InventoryItemPriceHistory(models.Model):
    """История цен (закупочная/продажная)"""

    class PriceType(models.TextChoices):
        PURCHASE = "purchase", "Закупочная"
        SELLING = "selling", "Продажная"

    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="price_history"
    )
    price_type = models.CharField(max_length=10, choices=PriceType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "История цены"
        verbose_name_plural = "История цен"
        indexes = [models.Index(fields=["item", "price_type", "changed_at"])]


class InventoryItemCostHistory(models.Model):
    """История себестоимости по приемкам"""

    class SourceType(models.TextChoices):
        AD_HOC = "ad_hoc", "Приемка без заказа"
        PO = "purchase_order", "Заказ поставщику"

    item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="cost_history"
    )
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.IntegerField(
        null=True, blank=True
    )  # id PurchaseOrder или None для ad_hoc
    cost_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField()
    received_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "История себестоимости"
        verbose_name_plural = "История себестоимости"
        indexes = [models.Index(fields=["item", "received_at"])]
