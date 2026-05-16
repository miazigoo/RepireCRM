"""Central registry of CRM permissions shown in the admin UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    codename: str
    name: str
    category: str
    description: str


PERMISSION_DEFINITIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        "orders.view_order",
        "Просматривать заказы",
        "orders",
        "Открывать страницу заказов и видеть заказы выбранного филиала.",
    ),
    PermissionDefinition(
        "orders.add_order",
        "Создавать заказы",
        "orders",
        "Принимать устройства и оформлять новые сервисные заказы.",
    ),
    PermissionDefinition(
        "orders.change_order",
        "Редактировать заказы",
        "orders",
        "Менять данные заказа, описание работ, стоимость и исполнителя.",
    ),
    PermissionDefinition(
        "orders.delete_order",
        "Удалять заказы",
        "orders",
        "Удалять ошибочно созданные заказы.",
    ),
    PermissionDefinition(
        "orders.change_status",
        "Менять статус заказа",
        "orders",
        "Переводить заказ между этапами ремонта и выдачи.",
    ),
    PermissionDefinition(
        "orders.view_all_shops",
        "Видеть заказы всех филиалов",
        "orders",
        "Доступ к заказам по всем филиалам вместо только выбранного магазина.",
    ),
    PermissionDefinition(
        "customers.view_customer",
        "Просматривать клиентов",
        "customers",
        "Открывать раздел клиентов и карточки клиентов выбранного филиала.",
    ),
    PermissionDefinition(
        "customers.add_customer",
        "Добавлять клиентов",
        "customers",
        "Создавать новые карточки клиентов.",
    ),
    PermissionDefinition(
        "customers.change_customer",
        "Редактировать клиентов",
        "customers",
        "Менять контакты, заметки и параметры клиента.",
    ),
    PermissionDefinition(
        "customers.delete_customer",
        "Удалять клиентов",
        "customers",
        "Удалять карточки клиентов.",
    ),
    PermissionDefinition(
        "inventory.view_inventory",
        "Открывать раздел склада",
        "inventory",
        "Видеть складскую страницу и складовые виджеты.",
    ),
    PermissionDefinition(
        "inventory.view_item",
        "Просматривать товары",
        "inventory",
        "Видеть товары, запчасти и расходники.",
    ),
    PermissionDefinition(
        "inventory.add_item",
        "Добавлять товары",
        "inventory",
        "Создавать карточки товаров и запчастей.",
    ),
    PermissionDefinition(
        "inventory.change_item",
        "Редактировать товары",
        "inventory",
        "Менять карточки товаров, штрихкоды и параметры учета.",
    ),
    PermissionDefinition(
        "inventory.view_stock",
        "Просматривать остатки",
        "inventory",
        "Видеть остатки и наличие по выбранному филиалу.",
    ),
    PermissionDefinition(
        "inventory.view_other_shop_stock",
        "Смотреть остатки других филиалов",
        "inventory",
        "Проверять наличие товаров в филиалах, которые не выбраны текущими.",
    ),
    PermissionDefinition(
        "inventory.add_movement",
        "Двигать склад",
        "inventory",
        "Создавать приемки, списания, перемещения и корректировки остатков.",
    ),
    PermissionDefinition(
        "inventory.view_purchase_orders",
        "Просматривать заказы поставщикам",
        "inventory",
        "Видеть закупки и заказы поставщикам.",
    ),
    PermissionDefinition(
        "inventory.view_purchase_requests",
        "Просматривать заявки на закупку",
        "inventory",
        "Видеть внутренние заявки склада на закупку товаров.",
    ),
    PermissionDefinition(
        "inventory.add_purchase_order",
        "Создавать заказы поставщикам",
        "inventory",
        "Оформлять новые закупки и заявки поставщикам.",
    ),
    PermissionDefinition(
        "inventory.add_purchase_request",
        "Создавать заявки на закупку",
        "inventory",
        "Фиксировать потребность склада перед согласованием директором.",
    ),
    PermissionDefinition(
        "inventory.change_purchase_request",
        "Редактировать заявки на закупку",
        "inventory",
        "Назначать поставщиков, менять позиции и разбивать заявки.",
    ),
    PermissionDefinition(
        "inventory.approve_purchase_request",
        "Согласовывать заявки на закупку",
        "inventory",
        "Утверждать, отклонять и готовить заявки к отправке поставщикам.",
    ),
    PermissionDefinition(
        "inventory.receive_purchase_orders",
        "Принимать заказы поставщиков",
        "inventory",
        "Принимать поставки и увеличивать остатки по складу.",
    ),
    PermissionDefinition(
        "inventory.view_suppliers",
        "Просматривать поставщиков",
        "inventory",
        "Видеть справочник поставщиков.",
    ),
    PermissionDefinition(
        "inventory.add_sale",
        "Создавать розничные продажи",
        "inventory",
        "Оформлять продажи товаров со склада.",
    ),
    PermissionDefinition(
        "inventory.change_sale",
        "Редактировать розничные продажи",
        "inventory",
        "Менять состав и параметры розничных продаж до финализации.",
    ),
    PermissionDefinition(
        "inventory.view_reports",
        "Просматривать складские отчеты",
        "inventory",
        "Открывать отчеты по оборачиваемости и движению склада.",
    ),
    PermissionDefinition(
        "reports.view_dashboard",
        "Просматривать отчеты",
        "reports",
        "Открывать раздел отчетов и видеть основные метрики.",
    ),
    PermissionDefinition(
        "reports.view_financial",
        "Просматривать финансовые отчеты",
        "reports",
        "Видеть финансовые показатели и выручку.",
    ),
    PermissionDefinition(
        "reports.view_analytics",
        "Просматривать аналитику",
        "reports",
        "Видеть аналитику заказов и управленческие показатели.",
    ),
    PermissionDefinition(
        "reports.view_all_shops",
        "Видеть общую статистику",
        "reports",
        "Открывать сводные отчеты по всем филиалам.",
    ),
    PermissionDefinition(
        "reports.generate_reports",
        "Формировать отчеты",
        "reports",
        "Создавать отчеты по шаблонам.",
    ),
    PermissionDefinition(
        "reports.export_reports",
        "Экспортировать отчеты",
        "reports",
        "Скачивать отчеты в PDF/Excel.",
    ),
    PermissionDefinition(
        "tasks.view_task",
        "Просматривать задачи",
        "tasks",
        "Открывать раздел задач и видеть назначенные задачи.",
    ),
    PermissionDefinition(
        "tasks.add_task",
        "Создавать задачи",
        "tasks",
        "Назначать задачи сотрудникам, ролям или филиалам.",
    ),
    PermissionDefinition(
        "tasks.change_task",
        "Редактировать задачи",
        "tasks",
        "Менять статус, прогресс и параметры задач.",
    ),
    PermissionDefinition(
        "tasks.view_all_tasks",
        "Видеть задачи сотрудников",
        "tasks",
        "Просматривать задачи других сотрудников и филиалов.",
    ),
    PermissionDefinition(
        "tasks.view_template",
        "Просматривать шаблоны задач",
        "tasks",
        "Видеть готовые шаблоны задач.",
    ),
    PermissionDefinition(
        "finance.add_payment",
        "Создавать платежи",
        "finance",
        "Принимать оплату по заказам и продажам.",
    ),
    PermissionDefinition(
        "payments.add_payment",
        "Создавать платежи (совместимость)",
        "finance",
        "Технический дубль для старых интеграций платежей.",
    ),
    PermissionDefinition(
        "promotions.view_promotion",
        "Просматривать акции и промокоды",
        "marketing",
        "Открывать раздел акций, скидок и промокодов.",
    ),
    PermissionDefinition(
        "promotions.change_promotion",
        "Управлять акциями и промокодами",
        "marketing",
        "Создавать и редактировать акции, скидочные правила и промокоды.",
    ),
    PermissionDefinition(
        "promotions.apply_discount",
        "Применять скидки к заказам",
        "marketing",
        "Проверять промокоды и добавлять скидки в карточке заказа.",
    ),
    PermissionDefinition(
        "settings.view_shop",
        "Просматривать филиалы",
        "settings",
        "Видеть список филиалов и настройки выбранного филиала.",
    ),
    PermissionDefinition(
        "settings.add_shop",
        "Создавать филиалы",
        "settings",
        "Добавлять новые магазины/точки обслуживания.",
    ),
    PermissionDefinition(
        "settings.change_shop",
        "Редактировать филиалы",
        "settings",
        "Менять адрес, контакты и состояние филиала.",
    ),
    PermissionDefinition(
        "settings.delete_shop",
        "Отключать филиалы",
        "settings",
        "Деактивировать филиалы.",
    ),
    PermissionDefinition(
        "settings.view_all_shops",
        "Видеть все филиалы",
        "settings",
        "Видеть все филиалы организации, а не только привязанные к аккаунту.",
    ),
    PermissionDefinition(
        "settings.view_shop_settings",
        "Просматривать настройки филиала",
        "settings",
        "Открывать настройки выбранного филиала.",
    ),
    PermissionDefinition(
        "settings.change_shop_settings",
        "Изменять настройки филиала",
        "settings",
        "Менять рабочие часы, уведомления, реквизиты и параметры чеков.",
    ),
    PermissionDefinition(
        "users.view_user",
        "Просматривать сотрудников",
        "users",
        "Открывать список сотрудников и карточки пользователей.",
    ),
    PermissionDefinition(
        "users.add_user",
        "Создавать сотрудников",
        "users",
        "Добавлять новых пользователей системы.",
    ),
    PermissionDefinition(
        "users.change_user",
        "Редактировать сотрудников",
        "users",
        "Менять ФИО, контакты, роль и статус пользователя.",
    ),
    PermissionDefinition(
        "users.delete_user",
        "Удалять сотрудников",
        "users",
        "Удалять учетные записи сотрудников.",
    ),
    PermissionDefinition(
        "users.manage_shop_access",
        "Назначать филиалы сотрудникам",
        "users",
        "Привязывать магазины к аккаунтам сотрудников.",
    ),
    PermissionDefinition(
        "users.manage_compensation",
        "Настраивать оплату сотрудников",
        "users",
        "Задавать фикс за заказ, проценты с услуг и продаж товаров.",
    ),
    PermissionDefinition(
        "users.manage_permissions",
        "Управлять ролями и правами",
        "users",
        "Создавать роли и отмечать разрешения галочками.",
    ),
)


DEFAULT_ROLE_PERMISSIONS: dict[str, tuple[str, ...] | str] = {
    "director": "all",
    "admin": "all",
    "manager": (
        "orders.view_order",
        "orders.add_order",
        "orders.change_order",
        "orders.change_status",
        "customers.view_customer",
        "customers.add_customer",
        "customers.change_customer",
        "inventory.view_inventory",
        "inventory.view_item",
        "inventory.view_stock",
        "inventory.view_other_shop_stock",
        "inventory.view_purchase_requests",
        "inventory.add_purchase_request",
        "reports.view_dashboard",
        "reports.view_financial",
        "reports.view_analytics",
        "promotions.view_promotion",
        "promotions.apply_discount",
        "tasks.view_task",
        "tasks.add_task",
        "tasks.change_task",
        "tasks.view_all_tasks",
        "users.view_user",
    ),
    "technician": (
        "orders.view_order",
        "orders.change_order",
        "orders.change_status",
        "customers.view_customer",
        "inventory.view_item",
        "inventory.view_stock",
        "tasks.view_task",
        "tasks.change_task",
    ),
    "cashier": (
        "orders.view_order",
        "orders.change_status",
        "customers.view_customer",
        "customers.add_customer",
        "inventory.view_item",
        "inventory.view_stock",
        "inventory.add_sale",
        "finance.add_payment",
        "payments.add_payment",
        "promotions.view_promotion",
        "promotions.apply_discount",
    ),
}


CATEGORY_LABELS: dict[str, str] = {
    "orders": "Заказы",
    "customers": "Клиенты",
    "inventory": "Склад",
    "reports": "Отчеты",
    "tasks": "Задачи",
    "finance": "Финансы",
    "marketing": "Маркетинг и скидки",
    "settings": "Настройки",
    "users": "Пользователи и доступ",
}
