import random
from calendar import monthrange
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from analytics.services import AnalyticsService
from customers.models import Customer, CustomerShopHistory
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from finance.models import (
    CashRegister,
    CashRegisterAccess,
    Expense,
    ExpenseCategory,
    Payment,
    PaymentMethod,
)
from inventory.models import (
    Category,
    InventoryItem,
    InventoryItemBarcode,
    InventoryItemCostHistory,
    PurchaseOrder,
    PurchaseOrderItem,
    RetailSale,
    RetailSaleItem,
    StockBalance,
    StockMovement,
    Supplier,
    SupplierItem,
)
from orders.models import (
    AdditionalService,
    Order,
    OrderAuditLog,
    OrderService,
    OrderStatusHistory,
    RepairService,
    RepairStage,
)
from promotions.models import OrderDiscount, PromoCode, Promotion
from shops.models import Organization, Shop, ShopSettings
from shops.subscription_services import (
    ensure_default_subscription_plans,
    get_or_create_trial_subscription,
)
from users.models import Role

User = get_user_model()


DEMO_SHOPS = (
    {
        "code": "MSK01",
        "name": "Repair CRM Москва Центр",
        "address": "г. Москва, ул. Тверская, д. 1",
        "phone": "+7 (495) 123-45-67",
        "email": "msk@repair-crm.test",
        "prefix": "MSK",
        "organization": "ООО Ремонт Москва",
    },
    {
        "code": "SPB01",
        "name": "Repair CRM СПб Невский",
        "address": "г. Санкт-Петербург, Невский пр., д. 100",
        "phone": "+7 (812) 987-65-43",
        "email": "spb@repair-crm.test",
        "prefix": "SPB",
        "organization": "ООО Ремонт Север",
    },
    {
        "code": "KZN01",
        "name": "Repair CRM Казань",
        "address": "г. Казань, ул. Баумана, д. 33",
        "phone": "+7 (843) 222-10-20",
        "email": "kzn@repair-crm.test",
        "prefix": "KZN",
        "organization": "ООО Ремонт Волга",
    },
    {
        "code": "EKB01",
        "name": "Repair CRM Екатеринбург",
        "address": "г. Екатеринбург, пр. Ленина, д. 24",
        "phone": "+7 (343) 300-20-10",
        "email": "ekb@repair-crm.test",
        "prefix": "EKB",
        "organization": "ООО Ремонт Урал",
    },
)


FIRST_NAMES = (
    "Александр",
    "Дмитрий",
    "Иван",
    "Максим",
    "Артем",
    "Сергей",
    "Михаил",
    "Никита",
    "Анна",
    "Мария",
    "Екатерина",
    "Ольга",
    "Елена",
    "Дарья",
    "Полина",
    "Виктория",
)
LAST_NAMES = (
    "Иванов",
    "Петров",
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Соколов",
    "Морозов",
    "Волков",
    "Новиков",
    "Федоров",
    "Михайлова",
    "Семенова",
    "Павлова",
    "Козлова",
    "Николаева",
    "Орлова",
)
PROBLEMS = (
    "Разбит дисплей после падения",
    "Быстро разряжается аккумулятор",
    "Не работает разъем зарядки",
    "Попала влага, не включается",
    "Нет изображения, подсветка работает",
    "Не слышно собеседника",
    "Не работает камера",
    "Перегревается под нагрузкой",
    "Плохо ловит сеть",
    "Зависает при запуске приложений",
)


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def add_months(source, months: int):
    month = source.month - 1 + months
    year = source.year + month // 12
    month = month % 12 + 1
    day = min(source.day, monthrange(year, month)[1])
    return source.replace(year=year, month=month, day=day)


def make_aware_date(date_value, hour=12, minute=0):
    return timezone.make_aware(
        datetime.combine(date_value, time(hour=hour, minute=minute)),
        timezone.get_current_timezone(),
    )


def set_created_at(model, obj, created_at, **extra_fields):
    update = {"created_at": created_at}
    update.update(extra_fields)
    model.objects.filter(pk=obj.pk).update(**update)


class Command(BaseCommand):
    help = "Создание большой демо-базы для разработки и проверки аналитики"

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=12,
            help="Сколько последних месяцев заполнить заказами и финансами",
        )
        parser.add_argument(
            "--orders",
            type=int,
            default=720,
            help="Сколько демо-заказов создать суммарно по филиалам",
        )
        parser.add_argument(
            "--customers",
            type=int,
            default=240,
            help="Сколько демо-клиентов создать",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=20260509,
            help="Seed генератора, чтобы данные были повторяемыми",
        )
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Удалить ранее созданные demo-записи перед генерацией",
        )
        parser.add_argument(
            "--only-reset",
            action="store_true",
            help="Только удалить demo-записи и не создавать новые данные",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.random = random.Random(options["seed"])
        self.months = max(1, options["months"])
        self.orders_target = max(1, options["orders"])
        self.customers_target = max(1, options["customers"])

        self.stdout.write("Создание демо-данных Repair CRM...")
        call_command("init_permissions", verbosity=0)
        ensure_default_subscription_plans()

        if options["reset_demo"] or options["only_reset"]:
            self.reset_demo_data()
        if options["only_reset"]:
            self.stdout.write(self.style.SUCCESS("Demo-данные удалены."))
            return

        shops = self.create_shops()
        users = self.create_users(shops)
        payment_methods = self.create_payment_methods()
        cash_registers = self.create_cash_registers(shops, users["cashiers"])
        device_models = self.create_device_catalog()
        suppliers = self.create_suppliers()
        inventory_items = self.create_inventory(shops, suppliers, users["director"])
        services = self.create_services(shops, device_models)
        promo_codes = self.create_promotions(shops, users["director"])
        customers = self.create_customers(users["managers"])

        self.seed_stock_history(shops, inventory_items, users["director"])
        self.create_purchase_orders(
            shops, suppliers, inventory_items, users["managers"], payment_methods
        )
        self.create_orders(
            shops,
            customers,
            device_models,
            services,
            inventory_items,
            users,
            payment_methods,
            cash_registers,
            promo_codes,
        )
        self.create_retail_sales(
            shops, customers, inventory_items, users["cashiers"], payment_methods
        )
        self.create_expenses(shops, users, payment_methods)
        self.refresh_customer_stats(customers)
        self.refresh_analytics_snapshots(shops)

        self.stdout.write(self.style.SUCCESS("Демо-данные созданы."))
        self.stdout.write(f"Филиалы: {len(shops)}")
        self.stdout.write(
            f"Клиенты: {Customer.objects.filter(phone__startswith='+7908').count()}"
        )
        self.stdout.write(
            f"Заказы demo: {Order.objects.filter(notes__startswith='[demo]').count()}"
        )
        self.stdout.write(
            "Платежи demo: "
            f"{Payment.objects.filter(description__startswith='[demo]').count()}"
        )
        self.stdout.write("Пользователь: b00bs / QwsAzx@2000")

    def reset_demo_data(self):
        self.stdout.write("Очистка ранее созданных demo-данных...")
        OrderStatusHistory.objects.filter(order__notes__startswith="[demo]").delete()
        OrderAuditLog.objects.filter(order__notes__startswith="[demo]").delete()
        RepairStage.objects.filter(order__notes__startswith="[demo]").delete()
        OrderDiscount.objects.filter(order__notes__startswith="[demo]").delete()
        OrderService.objects.filter(order__notes__startswith="[demo]").delete()
        Payment.objects.filter(description__startswith="[demo]").delete()
        Expense.objects.filter(invoice_number__startswith="DEMO-").delete()
        RetailSaleItem.objects.filter(sale__notes__startswith="[demo]").delete()
        RetailSale.objects.filter(notes__startswith="[demo]").delete()
        StockMovement.objects.filter(notes__startswith="[demo]").delete()
        PurchaseOrderItem.objects.filter(
            purchase_order__notes__startswith="[demo]"
        ).delete()
        PurchaseOrder.objects.filter(notes__startswith="[demo]").delete()
        Order.objects.filter(notes__startswith="[demo]").delete()
        PromoCode.objects.filter(description__startswith="[demo]").delete()
        Promotion.objects.filter(description__startswith="[demo]").delete()
        StockBalance.objects.filter(
            shop__code__in=[s["code"] for s in DEMO_SHOPS]
        ).delete()
        InventoryItemCostHistory.objects.filter(notes__startswith="[demo]").delete()
        InventoryItemBarcode.objects.filter(item__sku__startswith="DEMO-").delete()
        SupplierItem.objects.filter(item__sku__startswith="DEMO-").delete()
        InventoryItem.objects.filter(sku__startswith="DEMO-").delete()
        Device.objects.filter(serial_number__startswith="DEMO-").delete()
        CustomerShopHistory.objects.filter(customer__phone__startswith="+7908").delete()
        Customer.objects.filter(phone__startswith="+7908").delete()

    def create_shops(self):
        shops = []
        for data in DEMO_SHOPS:
            shop, _ = Shop.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "address": data["address"],
                    "phone": data["phone"],
                    "email": data["email"],
                    "is_active": True,
                    "currency": "RUB",
                },
            )
            organization, _ = Organization.objects.update_or_create(
                name=data["organization"],
                defaults={
                    "inn": f"77{self.random.randrange(1000000000, 9999999999)}"[:10],
                    "address": data["address"],
                    "phone": data["phone"],
                    "email": data["email"],
                    "website": "https://repair-crm.test",
                },
            )
            ShopSettings.objects.update_or_create(
                shop=shop,
                defaults={
                    "order_number_prefix": data["prefix"],
                    "work_hours_start": "09:00",
                    "work_hours_end": "21:00",
                    "organization": organization,
                    "receipt_footer_text": "Спасибо за обращение в Repair CRM",
                },
            )
            get_or_create_trial_subscription(organization)
            shops.append(shop)
        return shops

    def create_users(self, shops):
        roles = {role.code: role for role in Role.objects.all()}

        director = self.upsert_user(
            "director",
            "Иван",
            "Директоров",
            "director@repair-crm.test",
            "director123",
            roles["director"],
            shops,
            shops[0],
            is_director=True,
        )
        b00bs = self.upsert_user(
            "b00bs",
            "Тест",
            "Пользователь",
            "b00bs@example.com",
            "QwsAzx@2000",
            roles["director"],
            shops,
            shops[0],
            is_director=True,
        )

        managers = []
        technicians = []
        cashiers = []
        for index, shop in enumerate(shops, start=1):
            managers.append(
                self.upsert_user(
                    f"manager_{shop.code.lower()}",
                    ("Анна", "Мария", "Олег", "Павел")[index - 1],
                    ("Менеджерова", "Кураторова", "Сервисов", "Админов")[index - 1],
                    f"manager_{shop.code.lower()}@repair-crm.test",
                    "manager123",
                    roles["manager"],
                    [shop],
                    shop,
                )
            )
            cashiers.append(
                self.upsert_user(
                    f"cashier_{shop.code.lower()}",
                    ("Елена", "Дарья", "Ирина", "Ксения")[index - 1],
                    ("Кассирова", "Финансова", "Счетова", "Оплатина")[index - 1],
                    f"cashier_{shop.code.lower()}@repair-crm.test",
                    "cashier123",
                    roles["cashier"],
                    [shop],
                    shop,
                )
            )
            for tech_index in range(1, 4):
                technicians.append(
                    self.upsert_user(
                        f"tech_{shop.code.lower()}_{tech_index}",
                        ("Артем", "Никита", "Сергей")[tech_index - 1],
                        ("Паяльников", "Диагностов", "Модулев")[tech_index - 1],
                        f"tech_{shop.code.lower()}_{tech_index}@repair-crm.test",
                        "tech123",
                        roles["technician"],
                        [shop],
                        shop,
                    )
                )

        return {
            "director": director,
            "b00bs": b00bs,
            "managers": managers,
            "technicians": technicians,
            "cashiers": cashiers,
        }

    def upsert_user(
        self,
        username,
        first_name,
        last_name,
        email,
        password,
        role,
        shops,
        current_shop,
        is_director=False,
    ):
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": role,
                "is_director": is_director,
                "current_shop": current_shop,
                "is_active": True,
            },
        )
        user.set_password(password)
        user.save(update_fields=["password", "updated_at"])
        user.shops.set(shops)
        return user

    def create_payment_methods(self):
        methods = {}
        for code, name, is_cash, fee_percent in (
            ("cash", "Наличные", True, "0"),
            ("bank_card", "Банковская карта", False, "1.9"),
            ("sbp", "СБП", False, "0.7"),
            ("bank_transfer", "Безналичный перевод", False, "0"),
        ):
            method = (
                PaymentMethod.objects.filter(code=code).first()
                or PaymentMethod.objects.filter(name=name).first()
            )
            defaults = {
                "code": code,
                "name": name,
                "description": "Демо-способ оплаты",
                "is_cash": is_cash,
                "is_active": True,
                "fee_percent": money(fee_percent),
                "fee_fixed": money("0"),
            }
            if method:
                for field, value in defaults.items():
                    setattr(method, field, value)
                method.save()
            else:
                method = PaymentMethod.objects.create(**defaults)
            methods[code] = method
        return methods

    def create_cash_registers(self, shops, cashiers):
        registers = {}
        for shop in shops:
            register, _ = CashRegister.objects.update_or_create(
                shop=shop,
                name=f"Основная касса {shop.code}",
                defaults={"cash_balance": money(self.random.randrange(35000, 180000))},
            )
            for cashier in cashiers:
                if cashier.current_shop_id == shop.id:
                    CashRegisterAccess.objects.get_or_create(
                        user=cashier,
                        cash_register=register,
                        defaults={"is_manager": True},
                    )
            registers[shop.id] = register
        return registers

    def create_device_catalog(self):
        phone = DeviceType.objects.get_or_create(
            name="Смартфон", defaults={"icon": "phone"}
        )[0]
        tablet = DeviceType.objects.get_or_create(
            name="Планшет", defaults={"icon": "tablet"}
        )[0]
        laptop = DeviceType.objects.get_or_create(
            name="Ноутбук", defaults={"icon": "laptop"}
        )[0]
        watch = DeviceType.objects.get_or_create(
            name="Смарт-часы", defaults={"icon": "watch"}
        )[0]

        catalog = []
        phone_models = {
            "Apple": [
                "iPhone 11",
                "iPhone 12",
                "iPhone 12 Pro",
                "iPhone 13",
                "iPhone 13 Pro",
                "iPhone 14",
                "iPhone 14 Pro",
                "iPhone 15",
                "iPhone 15 Pro",
                "iPhone 15 Pro Max",
                "iPhone 16",
                "iPhone 16 Pro",
            ],
            "Samsung": [
                "Galaxy S21",
                "Galaxy S22",
                "Galaxy S23",
                "Galaxy S24",
                "Galaxy A15",
                "Galaxy A25",
                "Galaxy A35",
                "Galaxy A55",
                "Galaxy M34",
                "Galaxy Z Flip5",
                "Galaxy Z Fold5",
                "Galaxy Z Flip6",
            ],
            "Xiaomi": [
                "12",
                "12T",
                "13",
                "13T",
                "13T Pro",
                "14",
                "14 Ultra",
                "Mi 11 Lite",
            ],
            "Redmi": [
                "Note 10",
                "Note 11",
                "Note 12",
                "Note 12 Pro",
                "Note 13",
                "Note 13 Pro",
                "Note 13 Pro+",
                "12C",
                "13C",
            ],
            "POCO": ["M5", "M6 Pro", "X5", "X5 Pro", "X6", "X6 Pro", "F5", "F6"],
            "Realme": ["C55", "C67", "10", "11 Pro", "12", "12 Pro", "12 Pro+"],
            "Honor": ["70", "90", "90 Lite", "X8a", "X9a", "X9b", "Magic5 Pro"],
            "Huawei": ["P50 Pro", "P60 Pro", "Nova 10", "Nova 11", "Nova Y91"],
            "Tecno": ["Spark 10", "Spark 20", "Camon 20", "Camon 30", "Pova 5"],
            "Infinix": ["Hot 30", "Hot 40", "Note 30", "Note 40", "Zero 30"],
            "OnePlus": ["9", "10 Pro", "11", "12", "Nord 3", "Nord CE 3"],
            "Google": ["Pixel 6", "Pixel 7", "Pixel 7a", "Pixel 8", "Pixel 8 Pro"],
            "Vivo": ["V27", "V29", "Y35", "Y36", "Y100"],
            "OPPO": ["A78", "A98", "Reno 8", "Reno 10", "Find X5"],
        }
        for brand_name, names in phone_models.items():
            for index, model_name in enumerate(names, start=1):
                catalog.append((brand_name, model_name, phone, 2020 + index % 5))

        for brand_name, names, device_type in (
            (
                "Apple",
                ["iPad 9", "iPad 10", "iPad Air 5", "iPad Pro 11", "iPad Pro 12.9"],
                tablet,
            ),
            (
                "Samsung",
                ["Galaxy Tab A8", "Galaxy Tab A9", "Galaxy Tab S8", "Galaxy Tab S9"],
                tablet,
            ),
            (
                "Lenovo",
                ["Tab M10", "IdeaPad 3", "IdeaPad 5", "Legion 5"],
                tablet,
            ),
            (
                "Apple",
                ["MacBook Air M1", "MacBook Air M2", "MacBook Pro 14"],
                laptop,
            ),
            (
                "ASUS",
                ["VivoBook 15", "ZenBook 14", "TUF Gaming F15", "ROG Strix G16"],
                laptop,
            ),
            (
                "Acer",
                ["Aspire 5", "Swift 3", "Nitro 5"],
                laptop,
            ),
            (
                "HP",
                ["Pavilion 15", "Envy 13", "Victus 16"],
                laptop,
            ),
            (
                "Samsung",
                ["Galaxy Watch4", "Galaxy Watch5", "Galaxy Watch6"],
                watch,
            ),
            (
                "Apple",
                ["Watch SE", "Watch Series 8", "Watch Series 9"],
                watch,
            ),
        ):
            for index, model_name in enumerate(names, start=1):
                catalog.append((brand_name, model_name, device_type, 2020 + index % 5))

        models = []
        for brand_name, model_name, device_type, year in catalog:
            brand = DeviceBrand.objects.get_or_create(name=brand_name)[0]
            model, _ = DeviceModel.objects.update_or_create(
                brand=brand,
                name=model_name,
                defaults={
                    "device_type": device_type,
                    "model_number": (
                        f"DEMO-{brand_name[:3].upper()}-"
                        f"{abs(hash(model_name)) % 9999:04d}"
                    ),
                    "release_year": year,
                    "is_active": True,
                },
            )
            models.append(model)
        return models

    def create_suppliers(self):
        suppliers = []
        for index, name in enumerate(
            (
                "Мобайл Партс",
                "ПрофиКомплект",
                "ТехноОпт",
                "Северные Запчасти",
                "Урал Дисплей",
                "Аксессуар Маркет",
            ),
            start=1,
        ):
            supplier, _ = Supplier.objects.update_or_create(
                name=name,
                defaults={
                    "contact_person": f"Поставщик {index}",
                    "email": f"supplier{index}@repair-crm.test",
                    "phone": f"+74950000{index:03d}",
                    "payment_terms": "Постоплата 7 дней",
                    "delivery_terms": "Доставка 1-3 дня",
                    "min_order_amount": money(15000 + index * 5000),
                    "rating": money("4.5"),
                    "is_active": True,
                },
            )
            suppliers.append(supplier)
        return suppliers

    def create_inventory(self, shops, suppliers, created_by):
        categories = {
            name: Category.objects.get_or_create(name=name)[0]
            for name in (
                "Дисплеи",
                "Аккумуляторы",
                "Разъемы",
                "Камеры",
                "Корпусные детали",
                "Аксессуары",
                "Расходники",
                "Инструменты",
            )
        }
        item_specs = []
        for category, names in (
            (
                "Дисплеи",
                [
                    "Дисплей iPhone 13 OLED",
                    "Дисплей iPhone 14 OLED",
                    "Дисплей Samsung A55",
                    "Дисплей Redmi Note 13",
                    "Дисплей Honor 90",
                    "Дисплей Realme 12 Pro",
                ],
            ),
            (
                "Аккумуляторы",
                [
                    "АКБ iPhone 12",
                    "АКБ iPhone 13",
                    "АКБ Samsung S23",
                    "АКБ Redmi Note 12",
                    "АКБ Xiaomi 13T",
                    "АКБ Honor X9b",
                ],
            ),
            (
                "Разъемы",
                [
                    "Разъем Type-C универсальный",
                    "Разъем Lightning iPhone",
                    "Шлейф зарядки Samsung A-серия",
                    "Шлейф зарядки Redmi",
                ],
            ),
            (
                "Камеры",
                [
                    "Камера iPhone 13 основная",
                    "Камера Samsung S23",
                    "Камера Redmi Note 13",
                ],
            ),
            (
                "Корпусные детали",
                [
                    "Задняя крышка iPhone 14",
                    "Задняя крышка Samsung S24",
                    "Рамка Redmi Note 12",
                    "Кнопки громкости универсальные",
                ],
            ),
            (
                "Аксессуары",
                [
                    "Чехол прозрачный iPhone",
                    "Чехол Samsung A-серия",
                    "Защитное стекло 6.1",
                    "Защитное стекло 6.7",
                    "Зарядное устройство 20W",
                    "Кабель Type-C 1м",
                    "Кабель Lightning 1м",
                ],
            ),
            (
                "Расходники",
                [
                    "Клей B7000",
                    "Скотч дисплейный",
                    "Изопропиловый спирт",
                    "Салфетки безворсовые",
                ],
            ),
            (
                "Инструменты",
                [
                    "Набор отверток",
                    "Пинцет антистатический",
                    "Присоска для дисплеев",
                    "Фен термовоздушный",
                ],
            ),
        ):
            for name in names:
                item_specs.append((category, name))

        items = []
        for index, (category_name, item_name) in enumerate(item_specs, start=1):
            purchase = money(self.random.randrange(150, 9000))
            selling = money(
                purchase * money(self.random.choice(("1.35", "1.55", "1.8")))
            )
            supplier = suppliers[index % len(suppliers)]
            item, _ = InventoryItem.objects.update_or_create(
                sku=f"DEMO-{index:04d}",
                defaults={
                    "name": item_name,
                    "barcode": f"4609000{index:06d}",
                    "item_type": InventoryItem.ItemType.ACCESSORY
                    if category_name == "Аксессуары"
                    else InventoryItem.ItemType.COMPONENT,
                    "category": categories[category_name],
                    "description": "Демо-товар для проверки склада и отчетов",
                    "purchase_price": purchase,
                    "selling_price": selling,
                    "markup_percent": money(((selling - purchase) / purchase) * 100),
                    "primary_supplier": supplier,
                    "created_by": created_by,
                    "is_active": True,
                },
            )
            SupplierItem.objects.update_or_create(
                supplier=supplier,
                item=item,
                defaults={
                    "supplier_sku": f"{supplier.id}-{item.sku}",
                    "supplier_price": purchase,
                    "min_order_qty": self.random.randrange(1, 5),
                    "delivery_days": self.random.randrange(1, 8),
                    "is_preferred": True,
                },
            )
            InventoryItemBarcode.objects.get_or_create(
                item=item,
                barcode=f"200{index:010d}",
                defaults={"supplier": supplier},
            )
            for shop in shops:
                StockBalance.objects.update_or_create(
                    shop=shop,
                    item=item,
                    defaults={
                        "quantity": self.random.randrange(8, 120),
                        "reserved_quantity": self.random.randrange(0, 5),
                        "min_quantity": self.random.randrange(3, 12),
                        "max_quantity": self.random.randrange(60, 180),
                        "reorder_point": self.random.randrange(8, 20),
                        "location": f"Зона {self.random.choice(('A', 'B', 'C'))}",
                        "shelf": (
                            f"{self.random.randrange(1, 9)}-"
                            f"{self.random.randrange(1, 5)}"
                        ),
                    },
                )
            items.append(item)
        return items

    def create_services(self, shops, device_models):
        service_specs = (
            ("Замена дисплея", "other", 6900),
            ("Замена аккумулятора", "other", 3900),
            ("Замена разъема зарядки", "other", 3200),
            ("Чистка после влаги", "cleaning", 4500),
            ("Диагностика расширенная", "other", 1200),
            ("Перепрошивка ПО", "software", 1800),
            ("Восстановление данных", "software", 5500),
            ("Замена камеры", "other", 4200),
            ("Замена корпуса", "other", 5200),
            ("Защитное стекло", "protection", 900),
            ("Гидрогелевая пленка", "protection", 1200),
            ("Чехол", "accessories", 1700),
        )
        services = []
        for name, category, price in service_specs:
            service, _ = AdditionalService.objects.update_or_create(
                name=name,
                defaults={
                    "category": category,
                    "description": "Демо-услуга для заказов и отчетов",
                    "price": money(price),
                    "is_active": True,
                },
            )
            service.shops.set(shops)
            services.append(service)

            for model in device_models[:20]:
                RepairService.objects.update_or_create(
                    code=f"DEMO-{model.id}-{name.lower().replace(' ', '-')[:24]}",
                    defaults={
                        "name": name,
                        "device_type": model.device_type,
                        "brand": model.brand,
                        "model": model,
                        "default_price": money(price),
                        "avg_hours": money(self.random.choice(("1.5", "2.0", "3.5"))),
                        "warranty_days": self.random.choice((30, 60, 90, 180)),
                        "diagnostics_required": name.startswith("Диагностика"),
                        "notes": "[demo] типовая работа",
                        "is_active": True,
                    },
                )
        return services

    def create_promotions(self, shops, director):
        specs = (
            ("DEMO-SPRING7", "Сезонная скидка на ремонт", "percent", 7, None, 2500),
            ("DEMO-GLASS500", "Защитное стекло дешевле", "fixed", 500, None, 1500),
            ("DEMO-VIP12", "VIP клиент", "percent", 12, 2000, 6000),
        )
        promo_codes = []
        now = timezone.now()
        for code, name, discount_type, value, max_discount, min_amount in specs:
            promotion, _ = Promotion.objects.update_or_create(
                name=name,
                defaults={
                    "description": "[demo] акция для проверки скидок и промокодов",
                    "discount_type": discount_type,
                    "value": money(value),
                    "max_discount_amount": money(max_discount)
                    if max_discount is not None
                    else None,
                    "min_order_amount": money(min_amount),
                    "starts_at": now - timedelta(days=45),
                    "ends_at": now + timedelta(days=320),
                    "is_active": True,
                    "auto_apply": False,
                    "stackable": False,
                    "usage_limit": None,
                    "per_customer_limit": 3,
                    "created_by": director,
                },
            )
            promotion.shops.set(shops)
            promo_code, _ = PromoCode.objects.update_or_create(
                code=code,
                defaults={
                    "promotion": promotion,
                    "description": "[demo] промокод для заказов",
                    "is_active": True,
                    "starts_at": now - timedelta(days=45),
                    "ends_at": now + timedelta(days=320),
                    "usage_limit": None,
                    "per_customer_limit": 3,
                },
            )
            promo_codes.append(promo_code)
        return promo_codes

    def create_customers(self, managers):
        customers = []
        sources = [choice[0] for choice in Customer.CustomerSource.choices]
        for index in range(1, self.customers_target + 1):
            first_name = self.random.choice(FIRST_NAMES)
            last_name = self.random.choice(LAST_NAMES)
            created_at = self.random_date_in_period()
            customer, _ = Customer.objects.update_or_create(
                phone=f"+7908{index:07d}",
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"client{index:04d}@repair-crm.test",
                    "source": self.random.choice(sources),
                    "source_details": "demo",
                    "notes": "[demo] клиент для тестирования",
                    "created_by": self.random.choice(managers),
                    "preferred_channel": self.random.choice(("email", "sms", "")),
                    "marketing_consent": self.random.random() > 0.35,
                },
            )
            Customer.objects.filter(pk=customer.pk).update(
                created_at=created_at,
                updated_at=created_at,
            )
            customers.append(customer)
        return customers

    def seed_stock_history(self, shops, items, user):
        first_date = self.period_months()[0]
        for shop in shops:
            for item in items:
                balance = StockBalance.objects.get(shop=shop, item=item)
                created_at = make_aware_date(first_date, hour=9)
                movement = StockMovement.objects.create(
                    stock_balance=balance,
                    movement_type=StockMovement.MovementType.RECEIPT,
                    quantity_before=0,
                    quantity_change=balance.quantity,
                    quantity_after=balance.quantity,
                    reference_number=f"DEMO-OPEN-{shop.code}-{item.sku}",
                    notes="[demo] стартовый остаток",
                    cost_per_unit=item.purchase_price,
                    created_by=user,
                )
                set_created_at(StockMovement, movement, created_at)
                InventoryItemCostHistory.objects.create(
                    item=item,
                    shop=shop,
                    source_type=InventoryItemCostHistory.SourceType.AD_HOC,
                    cost_per_unit=item.purchase_price,
                    quantity=balance.quantity,
                    received_at=created_at,
                    notes="[demo] стартовый остаток",
                )

    def create_purchase_orders(
        self, shops, suppliers, items, managers, payment_methods
    ):
        for month_index, month_date in enumerate(self.period_months(), start=1):
            for shop in shops:
                manager = self.user_for_shop(managers, shop)
                supplier = self.random.choice(suppliers)
                order_date = make_aware_date(
                    month_date + timedelta(days=self.random.randrange(0, 20)),
                    hour=11,
                )
                purchase_order = PurchaseOrder.objects.create(
                    supplier=supplier,
                    shop=shop,
                    status=PurchaseOrder.OrderStatus.RECEIVED,
                    expected_delivery_date=order_date + timedelta(days=4),
                    actual_delivery_date=order_date + timedelta(days=3),
                    notes="[demo] регулярная закупка склада",
                    created_by=manager,
                    approved_by=manager,
                )
                subtotal = money("0")
                for item in self.random.sample(items, k=min(5, len(items))):
                    quantity = self.random.randrange(3, 18)
                    unit_price = item.purchase_price
                    PurchaseOrderItem.objects.create(
                        purchase_order=purchase_order,
                        item=item,
                        ordered_quantity=quantity,
                        received_quantity=quantity,
                        unit_price=unit_price,
                        total_price=unit_price * quantity,
                        supplier_sku=f"{supplier.id}-{item.sku}",
                    )
                    subtotal += unit_price * quantity
                    balance = StockBalance.objects.get(shop=shop, item=item)
                    before = balance.quantity
                    balance.quantity += quantity
                    balance.save()
                    movement = StockMovement.objects.create(
                        stock_balance=balance,
                        movement_type=StockMovement.MovementType.RECEIPT,
                        quantity_before=before,
                        quantity_change=quantity,
                        quantity_after=balance.quantity,
                        purchase_order=purchase_order,
                        reference_number=purchase_order.order_number,
                        notes="[demo] поступление по заказу поставщику",
                        cost_per_unit=unit_price,
                        created_by=manager,
                    )
                    set_created_at(
                        StockMovement, movement, order_date + timedelta(days=3)
                    )

                purchase_order.subtotal = subtotal
                purchase_order.tax_amount = money(subtotal * money("0.20"))
                purchase_order.total_amount = subtotal + purchase_order.tax_amount
                purchase_order.save(
                    update_fields=["subtotal", "tax_amount", "total_amount"]
                )
                PurchaseOrder.objects.filter(pk=purchase_order.pk).update(
                    order_date=order_date,
                    created_at=order_date,
                    updated_at=order_date + timedelta(days=3),
                )
                payment = self.create_payment(
                    payment_type=Payment.PaymentType.EXPENSE,
                    amount=purchase_order.total_amount,
                    method=payment_methods["bank_transfer"],
                    created_by=manager,
                    payment_date=order_date + timedelta(days=4),
                    description="[demo] оплата заказа поставщику",
                    purchase_order=purchase_order,
                    reference_number=purchase_order.order_number,
                )
                payment.external_id = f"DEMO-PO-{month_index}-{shop.code}"
                payment.save(update_fields=["external_id"])

    def create_orders(
        self,
        shops,
        customers,
        device_models,
        services,
        inventory_items,
        users,
        payment_methods,
        cash_registers,
        promo_codes,
    ):
        statuses = [
            Order.StatusChoices.COMPLETED,
            Order.StatusChoices.COMPLETED,
            Order.StatusChoices.COMPLETED,
            Order.StatusChoices.READY,
            Order.StatusChoices.IN_REPAIR,
            Order.StatusChoices.WAITING_PARTS,
            Order.StatusChoices.DIAGNOSED,
            Order.StatusChoices.RECEIVED,
            Order.StatusChoices.CANCELLED,
        ]
        priorities = [choice[0] for choice in Order.PriorityChoices.choices]
        completed_orders = []
        for index in range(1, self.orders_target + 1):
            shop = self.random.choice(shops)
            manager = self.user_for_shop(users["managers"], shop)
            technician = self.user_for_shop(users["technicians"], shop)
            customer = self.random.choice(customers)
            model = self.random.choice(device_models)
            created_at = self.random_date_in_period()
            status = self.random.choice(statuses)
            is_completed = status == Order.StatusChoices.COMPLETED
            estimate = money(self.random.randrange(1200, 18000))
            final_cost = (
                money(estimate + self.random.randrange(-500, 6500))
                if is_completed or status == Order.StatusChoices.READY
                else None
            )
            if final_cost is not None and final_cost < money("700"):
                final_cost = money("700")

            device = Device.objects.create(
                model=model,
                serial_number=f"DEMO-{index:06d}",
                imei=f"35{index:013d}"[:15],
                color=self.random.choice(("черный", "белый", "синий", "зеленый", "")),
                storage_capacity=self.random.choice(("64 ГБ", "128 ГБ", "256 ГБ", "")),
            )
            set_created_at(Device, device, created_at)

            completed_at = None
            estimated_completion = created_at + timedelta(
                days=self.random.randrange(1, 8)
            )
            if is_completed:
                completed_at = created_at + timedelta(days=self.random.randrange(1, 9))
            order = Order.objects.create(
                shop=shop,
                customer=customer,
                device=device,
                status=status,
                priority=self.random.choice(priorities),
                problem_description=self.random.choice(PROBLEMS),
                diagnosis=self.random.choice(
                    (
                        "Требуется замена модуля",
                        "Износ аккумулятора",
                        "Поврежден шлейф",
                        "Следы влаги на плате",
                        "Программный сбой",
                    )
                ),
                work_description="Выполнены диагностика и ремонтные работы"
                if is_completed
                else "",
                accessories=self.random.choice(("коробка", "зарядка", "чехол", "")),
                device_condition=self.random.choice(
                    ("царапины на корпусе", "сколы по углам", "без видимых повреждений")
                ),
                cost_estimate=estimate,
                final_cost=final_cost,
                prepayment=money("0"),
                created_by=manager,
                assigned_to=technician,
                estimated_completion=estimated_completion,
                completed_at=completed_at,
                notes="[demo] заказ для годовой аналитики",
                sla_on_time=(completed_at <= estimated_completion)
                if completed_at
                else None,
                sla_delay_minutes=int(
                    (completed_at - estimated_completion).total_seconds() / 60
                )
                if completed_at
                else None,
            )
            Order.objects.filter(pk=order.pk).update(
                created_at=created_at,
                updated_at=completed_at or created_at,
                completed_at=completed_at,
            )
            self.attach_services(order, services)
            self.attach_discount(order, promo_codes, manager)
            self.consume_inventory(order, inventory_items, technician, created_at)
            self.create_order_history(
                order, manager, technician, created_at, completed_at
            )

            if is_completed:
                completed_orders.append(order)
                amount = order.total_cost
                method = self.random.choice(
                    (
                        payment_methods["cash"],
                        payment_methods["bank_card"],
                        payment_methods["sbp"],
                    )
                )
                register = cash_registers[shop.id] if method.is_cash else None
                self.create_payment(
                    payment_type=Payment.PaymentType.INCOME,
                    amount=amount,
                    method=method,
                    created_by=manager,
                    payment_date=completed_at,
                    description="[demo] оплата ремонта",
                    order=order,
                    cash_register=register,
                    reference_number=order.order_number,
                )
                Order.objects.filter(pk=order.pk).update(
                    prepayment=amount,
                    updated_at=completed_at,
                )
                if register:
                    register.cash_balance += amount
                    register.save(update_fields=["cash_balance"])
            elif status in (Order.StatusChoices.READY, Order.StatusChoices.IN_REPAIR):
                Order.objects.filter(pk=order.pk).update(
                    prepayment=money(order.cost_estimate * money("0.35")),
                    updated_at=created_at + timedelta(hours=6),
                )

        self.create_warranty_cases(completed_orders, users)

    def attach_services(self, order, services):
        selected = self.random.sample(services, k=self.random.randrange(1, 4))
        for service in selected:
            OrderService.objects.update_or_create(
                order=order,
                service=service,
                defaults={
                    "quantity": 1
                    if service.category != "accessories"
                    else self.random.randrange(1, 3),
                    "price": service.price,
                },
            )

    def attach_discount(self, order, promo_codes, manager):
        if not promo_codes or self.random.random() > 0.28:
            return
        promo_code = self.random.choice(promo_codes)
        if (
            promo_code.promotion.shops.exists()
            and not promo_code.promotion.shops.filter(id=order.shop_id).exists()
        ):
            return
        amount = promo_code.promotion.calculate_discount(order.subtotal_before_discount)
        if amount <= 0:
            return
        OrderDiscount.objects.update_or_create(
            order=order,
            promo_code=promo_code,
            defaults={
                "promotion": promo_code.promotion,
                "source": OrderDiscount.Source.PROMO_CODE,
                "label": f"Промокод {promo_code.code}",
                "amount": amount,
                "created_by": manager,
            },
        )

    def consume_inventory(self, order, inventory_items, technician, created_at):
        for item in self.random.sample(inventory_items, k=self.random.randrange(1, 3)):
            balance = StockBalance.objects.filter(shop=order.shop, item=item).first()
            if not balance or balance.quantity <= 0:
                continue
            quantity = 1
            before = balance.quantity
            balance.quantity -= quantity
            balance.save()
            movement = StockMovement.objects.create(
                stock_balance=balance,
                movement_type=StockMovement.MovementType.SHIPMENT,
                quantity_before=before,
                quantity_change=-quantity,
                quantity_after=balance.quantity,
                repair_order=order,
                reference_number=order.order_number,
                notes="[demo] списание на ремонт",
                cost_per_unit=item.purchase_price,
                created_by=technician,
            )
            set_created_at(
                StockMovement,
                movement,
                created_at + timedelta(hours=self.random.randrange(4, 48)),
            )

    def create_order_history(
        self, order, manager, technician, created_at, completed_at
    ):
        received = OrderStatusHistory.objects.create(
            order=order,
            old_status="",
            new_status=Order.StatusChoices.RECEIVED,
            comment="Заказ принят",
            changed_by=manager,
        )
        OrderStatusHistory.objects.filter(pk=received.pk).update(changed_at=created_at)
        if order.status != Order.StatusChoices.RECEIVED:
            changed_at = created_at + timedelta(hours=8)
            diagnosed = OrderStatusHistory.objects.create(
                order=order,
                old_status=Order.StatusChoices.RECEIVED,
                new_status=Order.StatusChoices.DIAGNOSED,
                comment="Диагностика завершена",
                changed_by=technician,
            )
            OrderStatusHistory.objects.filter(pk=diagnosed.pk).update(
                changed_at=changed_at
            )
        if completed_at:
            done = OrderStatusHistory.objects.create(
                order=order,
                old_status=Order.StatusChoices.TESTING,
                new_status=Order.StatusChoices.COMPLETED,
                comment="Устройство выдано клиенту",
                changed_by=manager,
            )
            OrderStatusHistory.objects.filter(pk=done.pk).update(
                changed_at=completed_at
            )
            stage = RepairStage.objects.create(
                order=order,
                title="Финальная проверка",
                description="Проверены зарядка, экран, камера и связь",
                customer_visible=True,
                created_by=technician,
            )
            set_created_at(RepairStage, stage, completed_at - timedelta(hours=2))
        audit = OrderAuditLog.objects.create(
            order=order,
            action=OrderAuditLog.ActionChoices.CREATED,
            actor=manager,
            message="Создан demo-заказ",
            changes={"demo": True},
        )
        set_created_at(OrderAuditLog, audit, created_at)

    def create_warranty_cases(self, completed_orders, users):
        if not completed_orders:
            return

        target = max(6, min(len(completed_orders) // 12, 60))
        reasons = (
            "Брак установленной детали",
            "Повторная неисправность после ремонта",
            "Доделка после диагностики качества",
            "След от инструмента на корпусе",
            "Переделка пайки после нагрузки",
        )
        statuses = (
            Order.StatusChoices.COMPLETED,
            Order.StatusChoices.IN_REPAIR,
            Order.StatusChoices.RECEIVED,
        )

        for source in self.random.sample(
            completed_orders, k=min(target, len(completed_orders))
        ):
            created_at = source.completed_at + timedelta(
                days=self.random.randrange(5, 75),
                hours=self.random.randrange(1, 9),
            )
            status = self.random.choice(statuses)
            completed_at = (
                created_at + timedelta(days=self.random.randrange(1, 4))
                if status == Order.StatusChoices.COMPLETED
                else None
            )
            manager = self.user_for_shop(users["managers"], source.shop)
            technician = source.assigned_to or self.user_for_shop(
                users["technicians"], source.shop
            )
            reason = self.random.choice(reasons)
            warranty_order = Order.objects.create(
                shop=source.shop,
                customer=source.customer,
                device=source.device,
                status=status,
                priority=Order.PriorityChoices.HIGH,
                problem_description=f"[Гарантия] {reason.lower()}",
                diagnosis="Проверка гарантийного обращения",
                work_description="Гарантийная переделка выполнена"
                if completed_at
                else "",
                accessories=source.accessories,
                device_condition=source.device_condition,
                cost_estimate=money("0"),
                final_cost=money("0") if completed_at else None,
                prepayment=money("0"),
                created_by=manager,
                assigned_to=technician,
                estimated_completion=created_at + timedelta(days=3),
                completed_at=completed_at,
                notes=f"[demo][warranty] гарантийный случай по {source.order_number}",
                is_warranty_case=True,
                warranty_parent=source,
                warranty_reason=reason,
                warranty_days=source.warranty_days,
            )
            Order.objects.filter(pk=warranty_order.pk).update(
                created_at=created_at,
                updated_at=completed_at or created_at,
                completed_at=completed_at,
            )
            self.create_warranty_history(
                warranty_order, source, manager, technician, created_at, completed_at
            )

    def create_warranty_history(
        self,
        warranty_order,
        source_order,
        manager,
        technician,
        created_at,
        completed_at,
    ):
        received = OrderStatusHistory.objects.create(
            order=warranty_order,
            old_status="",
            new_status=Order.StatusChoices.RECEIVED,
            comment=f"Гарантийный случай по {source_order.order_number}",
            changed_by=manager,
        )
        OrderStatusHistory.objects.filter(pk=received.pk).update(changed_at=created_at)
        if completed_at:
            done = OrderStatusHistory.objects.create(
                order=warranty_order,
                old_status=Order.StatusChoices.IN_REPAIR,
                new_status=Order.StatusChoices.COMPLETED,
                comment="Гарантийная переделка завершена",
                changed_by=manager,
            )
            OrderStatusHistory.objects.filter(pk=done.pk).update(
                changed_at=completed_at
            )
            stage = RepairStage.objects.create(
                order=warranty_order,
                title="Контроль гарантии",
                description="Проверено после переделки, клиенту можно выдавать",
                customer_visible=True,
                created_by=technician,
            )
            set_created_at(RepairStage, stage, completed_at - timedelta(hours=1))

        audit = OrderAuditLog.objects.create(
            order=warranty_order,
            action=OrderAuditLog.ActionChoices.CREATED,
            actor=manager,
            message=f"Создан гарантийный demo-заказ по {source_order.order_number}",
            changes={"source_order_id": source_order.id, "demo": True},
        )
        set_created_at(OrderAuditLog, audit, created_at)

    def create_retail_sales(self, shops, customers, items, cashiers, payment_methods):
        accessories = (
            list(items.filter(category__name="Аксессуары"))
            if hasattr(items, "filter")
            else [item for item in items if item.category.name == "Аксессуары"]
        )
        if not accessories:
            accessories = list(items)
        for index in range(max(80, self.orders_target // 4)):
            shop = self.random.choice(shops)
            cashier = self.user_for_shop(cashiers, shop)
            created_at = self.random_date_in_period()
            sale = RetailSale.objects.create(
                shop=shop,
                cashier=cashier,
                customer=self.random.choice(customers),
                status=RetailSale.Status.COMPLETED,
                discount_amount=money(self.random.choice((0, 100, 200, 300))),
                notes="[demo] розничная продажа аксессуаров",
                completed_at=created_at,
            )
            subtotal = money("0")
            for item in self.random.sample(accessories, k=min(2, len(accessories))):
                quantity = self.random.randrange(1, 3)
                RetailSaleItem.objects.create(
                    sale=sale,
                    item=item,
                    quantity=quantity,
                    unit_price=item.selling_price,
                    total_price=item.selling_price * quantity,
                )
                subtotal += item.selling_price * quantity
            sale.subtotal = subtotal
            sale.save(update_fields=["subtotal", "total_amount"])
            RetailSale.objects.filter(pk=sale.pk).update(
                created_at=created_at,
                completed_at=created_at,
            )
            self.create_payment(
                payment_type=Payment.PaymentType.INCOME,
                amount=sale.total_amount,
                method=self.random.choice(
                    (payment_methods["cash"], payment_methods["sbp"])
                ),
                created_by=cashier,
                payment_date=created_at,
                description="[demo] розничная продажа",
                reference_number=sale.sale_number,
            )

    def create_expenses(self, shops, users, payment_methods):
        categories = {
            name: ExpenseCategory.objects.get_or_create(name=name)[0]
            for name in ("Зарплата", "Аренда", "Маркетинг", "Коммунальные", "Прочее")
        }
        for month_index, month_date in enumerate(self.period_months(), start=1):
            for shop in shops:
                manager = self.user_for_shop(users["managers"], shop)
                self.create_expense_with_payment(
                    shop=shop,
                    title=f"Зарплата сотрудников {shop.code}",
                    category=categories["Зарплата"],
                    expense_type=Expense.ExpenseType.SALARY,
                    amount=money(self.random.randrange(280000, 560000)),
                    date_value=month_date + timedelta(days=24),
                    created_by=manager,
                    payment_method=payment_methods["bank_transfer"],
                    invoice=f"DEMO-SALARY-{shop.code}-{month_index:02d}",
                    description="[demo] выплаты менеджерам, мастерам и кассирам",
                )
                self.create_expense_with_payment(
                    shop=shop,
                    title=f"Аренда помещения {shop.code}",
                    category=categories["Аренда"],
                    expense_type=Expense.ExpenseType.RENT,
                    amount=money(self.random.randrange(90000, 220000)),
                    date_value=month_date + timedelta(days=2),
                    created_by=manager,
                    payment_method=payment_methods["bank_transfer"],
                    invoice=f"DEMO-RENT-{shop.code}-{month_index:02d}",
                    description="[demo] аренда сервисного центра",
                )
                self.create_expense_with_payment(
                    shop=shop,
                    title=f"Маркетинг {shop.code}",
                    category=categories["Маркетинг"],
                    expense_type=Expense.ExpenseType.MARKETING,
                    amount=money(self.random.randrange(25000, 95000)),
                    date_value=month_date + timedelta(days=12),
                    created_by=manager,
                    payment_method=payment_methods["bank_card"],
                    invoice=f"DEMO-MARKETING-{shop.code}-{month_index:02d}",
                    description="[demo] реклама и лидогенерация",
                )

    def create_expense_with_payment(
        self,
        shop,
        title,
        category,
        expense_type,
        amount,
        date_value,
        created_by,
        payment_method,
        invoice,
        description,
    ):
        expense_date = min(date_value, timezone.localdate())
        expense = Expense.objects.create(
            title=title,
            category=category,
            expense_type=expense_type,
            amount=amount,
            shop=shop,
            description=description,
            invoice_number=invoice,
            is_approved=True,
            is_paid=True,
            expense_date=expense_date,
            approved_by=created_by,
            created_by=created_by,
        )
        created_at = make_aware_date(expense_date, hour=10)
        set_created_at(Expense, expense, created_at)
        self.create_payment(
            payment_type=Payment.PaymentType.EXPENSE,
            amount=amount,
            method=payment_method,
            created_by=created_by,
            payment_date=created_at,
            description="[demo] " + title.lower(),
            expense=expense,
            reference_number=invoice,
        )

    def create_payment(
        self,
        payment_type,
        amount,
        method,
        created_by,
        payment_date,
        description,
        cash_register=None,
        order=None,
        purchase_order=None,
        expense=None,
        reference_number="",
    ):
        fee = money(amount * (method.fee_percent / Decimal("100")) + method.fee_fixed)
        payment = Payment.objects.create(
            payment_type=payment_type,
            status=Payment.PaymentStatus.COMPLETED,
            amount=amount,
            fee_amount=fee,
            payment_method=method,
            cash_register=cash_register,
            order=order,
            purchase_order=purchase_order,
            expense=expense,
            description=description,
            reference_number=reference_number,
            payment_date=payment_date,
            processed_at=payment_date,
            created_by=created_by,
        )
        set_created_at(Payment, payment, payment_date)
        return payment

    def refresh_customer_stats(self, customers):
        for customer in customers:
            customer.update_statistics()
            for shop in Shop.objects.filter(
                code__in=[data["code"] for data in DEMO_SHOPS]
            ):
                if Order.objects.filter(customer=customer, shop=shop).exists():
                    history, _ = CustomerShopHistory.objects.get_or_create(
                        customer=customer,
                        shop=shop,
                    )
                    visits = Order.objects.filter(customer=customer, shop=shop).count()
                    last_order = Order.objects.filter(
                        customer=customer, shop=shop
                    ).latest("created_at")
                    CustomerShopHistory.objects.filter(pk=history.pk).update(
                        visits_count=visits,
                        first_visit=Order.objects.filter(customer=customer, shop=shop)
                        .earliest("created_at")
                        .created_at,
                        last_visit=last_order.created_at,
                    )

    def refresh_analytics_snapshots(self, shops):
        for month_date in self.period_months():
            AnalyticsService.save_monthly_revenue_snapshot(
                None, month_date.year, month_date.month
            )
            for shop in shops:
                AnalyticsService.save_monthly_revenue_snapshot(
                    shop.id, month_date.year, month_date.month
                )
            date_from = make_aware_date(month_date, hour=0)
            date_to = make_aware_date(
                month_date.replace(
                    day=monthrange(month_date.year, month_date.month)[1]
                ),
                hour=23,
                minute=59,
            )
            AnalyticsService.save_popular_services_snapshot(None, date_from, date_to)
            for shop in shops:
                AnalyticsService.save_popular_services_snapshot(
                    shop.id, date_from, date_to
                )

    def period_months(self):
        today = timezone.localdate()
        start = add_months(today.replace(day=1), -(self.months - 1))
        return [add_months(start, offset) for offset in range(self.months)]

    def random_date_in_period(self):
        month_date = self.random.choice(self.period_months())
        today = timezone.localdate()
        max_day = monthrange(month_date.year, month_date.month)[1]
        if month_date.year == today.year and month_date.month == today.month:
            max_day = min(max_day, today.day)
        day = self.random.randrange(1, max_day + 1)
        return make_aware_date(
            month_date.replace(day=day),
            hour=self.random.randrange(9, 20),
            minute=self.random.randrange(0, 60),
        )

    def user_for_shop(self, users, shop):
        scoped = [user for user in users if user.current_shop_id == shop.id]
        return self.random.choice(scoped or users)
