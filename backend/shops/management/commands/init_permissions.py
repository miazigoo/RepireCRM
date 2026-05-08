from django.core.management.base import BaseCommand

from users.models import Permission, Role
from users.permissions import DEFAULT_ROLE_PERMISSIONS, PERMISSION_DEFINITIONS


class Command(BaseCommand):
    help = "Инициализация базовых разрешений и ролей"

    def handle(self, *args, **options):
        permissions_by_codename = {}
        for definition in PERMISSION_DEFINITIONS:
            permission, created = Permission.objects.get_or_create(
                codename=definition.codename,
                defaults={
                    "name": definition.name,
                    "category": definition.category,
                    "description": definition.description,
                },
            )
            changed_fields = []
            for field in ("name", "category", "description"):
                value = getattr(definition, field)
                if getattr(permission, field) != value:
                    setattr(permission, field, value)
                    changed_fields.append(field)
            if changed_fields:
                permission.save(update_fields=changed_fields)
            permissions_by_codename[permission.codename] = permission
            if created:
                self.stdout.write(f"✅ Создано разрешение: {definition.name}")

        roles_data = [
            ("director", "Директор", "director"),
            ("manager", "Менеджер", "manager"),
            ("technician", "Техник", "technician"),
            ("cashier", "Кассир", "cashier"),
            ("admin", "Администратор", "admin"),
        ]

        for name, display_name, code in roles_data:
            role, created = Role.objects.get_or_create(
                code=code, defaults={"name": display_name}
            )
            role_rule = DEFAULT_ROLE_PERMISSIONS[code]
            if role_rule == "all":
                role_permissions = list(permissions_by_codename.values())
            else:
                role_permissions = [
                    permissions_by_codename[codename]
                    for codename in role_rule
                    if codename in permissions_by_codename
                ]
            role.permissions.add(*role_permissions)
            if created:
                self.stdout.write(f"✅ Создана роль: {display_name}")

        self.stdout.write(
            self.style.SUCCESS("Инициализация разрешений и ролей завершена!")
        )
