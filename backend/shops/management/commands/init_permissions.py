from django.core.management.base import BaseCommand

from users.models import Permission, Role


class Command(BaseCommand):
    help = "Инициализация базовых разрешений и ролей"

    def handle(self, *args, **options):
        # Создаем базовые разрешения
        permissions_data = [
            # Заказы
            ("orders.view_order", "Просмотр заказов", "orders"),
            ("orders.add_order", "Создание заказов", "orders"),
            ("orders.change_order", "Изменение заказов", "orders"),
            ("orders.delete_order", "Удаление заказов", "orders"),
            ("orders.change_status", "Изменение статуса заказа", "orders"),
            ("orders.view_all_shops", "Просмотр заказов всех магазинов", "orders"),
            # Клиенты
            ("customers.view_customer", "Просмотр клиентов", "customers"),
            ("customers.add_customer", "Добавление клиентов", "customers"),
            ("customers.change_customer", "Изменение клиентов", "customers"),
            ("customers.delete_customer", "Удаление клиентов", "customers"),
            # Склад
            ("inventory.view_inventory", "Просмотр склада", "inventory"),
            ("inventory.change_inventory", "Управление складом", "inventory"),
            ("inventory.view_item", "Просмотр товаров", "inventory"),
            ("inventory.add_item", "Создание товаров", "inventory"),
            ("inventory.view_stock", "Просмотр остатков", "inventory"),
            ("inventory.receive_stock", "Приемка остатков", "inventory"),
            ("inventory.adjust_stock", "Корректировка остатков", "inventory"),
            ("inventory.add_movement", "Создание движений склада", "inventory"),
            ("inventory.view_purchase", "Просмотр закупок", "inventory"),
            ("inventory.add_purchase", "Создание закупок", "inventory"),
            ("inventory.receive_purchase", "Приемка закупок", "inventory"),
            ("inventory.view_supplier", "Просмотр поставщиков", "inventory"),
            ("inventory.add_sale", "Создание продаж", "inventory"),
            ("inventory.change_sale", "Изменение продаж", "inventory"),
            ("inventory.view_reports", "Складские отчеты", "inventory"),
            # Отчеты
            ("reports.view_dashboard", "Дашборд отчетов", "reports"),
            ("reports.view_financial", "Финансовые отчеты", "reports"),
            ("reports.view_analytics", "Аналитические отчеты", "reports"),
            ("reports.generate_reports", "Генерация отчетов", "reports"),
            ("reports.export_reports", "Экспорт отчетов", "reports"),
            # Задачи
            ("tasks.view_task", "Просмотр задач", "tasks"),
            ("tasks.add_task", "Создание задач", "tasks"),
            ("tasks.change_task", "Изменение задач", "tasks"),
            ("tasks.view_template", "Просмотр шаблонов задач", "tasks"),
            # Финансы
            ("finance.add_payment", "Создание платежей", "finance"),
            ("payments.add_payment", "Создание платежей", "finance"),
            # Настройки
            ("settings.view_shop", "Просмотр филиалов", "settings"),
            ("settings.change_shop", "Изменение филиалов", "settings"),
            ("settings.view_shop_settings", "Просмотр настроек магазина", "settings"),
            (
                "settings.change_shop_settings",
                "Изменение настроек магазина",
                "settings",
            ),
            # Пользователи
            ("users.view_user", "Просмотр пользователей", "users"),
            ("users.add_user", "Добавление пользователей", "users"),
            ("users.change_user", "Изменение пользователей", "users"),
            ("users.delete_user", "Удаление пользователей", "users"),
            ("users.manage_permissions", "Управление правами доступа", "users"),
        ]

        permissions = []
        for codename, name, category in permissions_data:
            permission, created = Permission.objects.get_or_create(
                codename=codename, defaults={"name": name, "category": category}
            )
            permissions.append(permission)
            if created:
                self.stdout.write(f"✅ Создано разрешение: {name}")

        # Создаем роли
        roles_data = [
            ("director", "Директор", "director", permissions),
            (
                "manager",
                "Менеджер",
                "manager",
                [
                    p
                    for p in permissions
                    if p.category in ["orders", "customers", "reports"]
                ],
            ),
            (
                "technician",
                "Техник",
                "technician",
                [
                    p
                    for p in permissions
                    if p.category in ["orders"]
                    and "view" in p.codename
                    or "change_status" in p.codename
                ],
            ),
            (
                "cashier",
                "Кассир",
                "cashier",
                [
                    p
                    for p in permissions
                    if p.category in ["orders", "customers"] and "view" in p.codename
                ],
            ),
            ("admin", "Администратор", "admin", permissions),
        ]

        for name, display_name, code, role_permissions in roles_data:
            role, created = Role.objects.get_or_create(
                code=code, defaults={"name": display_name}
            )
            role.permissions.add(*role_permissions)
            if created:
                self.stdout.write(f"✅ Создана роль: {display_name}")

        self.stdout.write(
            self.style.SUCCESS("Инициализация разрешений и ролей завершена!")
        )
