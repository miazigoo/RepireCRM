from django.core.management.base import BaseCommand
from users.models import Permission, Role


class Command(BaseCommand):
    help = 'Инициализация базовых разрешений и ролей'

    def handle(self, *args, **options):
        # Создаем базовые разрешения
        permissions_data = [
            # Заказы
            ('orders.view_order', 'Просмотр заказов', 'orders'),
            ('orders.add_order', 'Создание заказов', 'orders'),
            ('orders.change_order', 'Изменение заказов', 'orders'),
            ('orders.delete_order', 'Удаление заказов', 'orders'),
            ('orders.change_status', 'Изменение статуса заказа', 'orders'),
            ('orders.view_all_shops', 'Просмотр заказов всех магазинов', 'orders'),

            # Клиенты
            ('customers.view_customer', 'Просмотр клиентов', 'customers'),
            ('customers.add_customer', 'Добавление клиентов', 'customers'),
            ('customers.change_customer', 'Изменение клиентов', 'customers'),
            ('customers.delete_customer', 'Удаление клиентов', 'customers'),

            # Склад
            ('inventory.view_inventory', 'Просмотр склада', 'inventory'),
            ('inventory.change_inventory', 'Управление складом', 'inventory'),

            # Отчеты
            ('reports.view_financial', 'Финансовые отчеты', 'reports'),
            ('reports.view_analytics', 'Аналитические отчеты', 'reports'),

            # Настройки
            ('settings.view_shop_settings', 'Просмотр настроек магазина', 'settings'),
            ('settings.change_shop_settings', 'Изменение настроек магазина', 'settings'),

            # Пользователи
            ('users.view_user', 'Просмотр пользователей', 'users'),
            ('users.add_user', 'Добавление пользователей', 'users'),
            ('users.change_user', 'Изменение пользователей', 'users'),
            ('users.delete_user', 'Удаление пользователей', 'users'),
            ('users.manage_permissions', 'Управление правами доступа', 'users'),
        ]

        permissions = []
        for codename, name, category in permissions_data:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name,
                    'category': category
                }
            )
            permissions.append(permission)
            if created:
                self.stdout.write(f'✅ Создано разрешение: {name}')

        # Создаем роли
        roles_data = [
            ('director', 'Директор', 'director', permissions),
            ('manager', 'Менеджер', 'manager', [
                p for p in permissions
                if p.category in ['orders', 'customers', 'reports']
            ]),
            ('technician', 'Техник', 'technician', [
                p for p in permissions
                if p.category in ['orders'] and 'view' in p.codename or 'change_status' in p.codename
            ]),
            ('cashier', 'Кассир', 'cashier', [
                p for p in permissions
                if p.category in ['orders', 'customers'] and 'view' in p.codename
            ]),
        ]

        for name, display_name, code, role_permissions in roles_data:
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    'name': display_name
                }
            )
            if created:
                role.permissions.set(role_permissions)
                self.stdout.write(f'✅ Создана роль: {display_name}')

        self.stdout.write(
            self.style.SUCCESS('Инициализация разрешений и ролей завершена!')
        )