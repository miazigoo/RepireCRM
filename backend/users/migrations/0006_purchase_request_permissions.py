from django.db import migrations

NEW_PERMISSIONS = (
    (
        "inventory.view_purchase_requests",
        "Просматривать заявки на закупку",
        "inventory",
        "Видеть внутренние заявки склада на закупку товаров.",
    ),
    (
        "inventory.add_purchase_request",
        "Создавать заявки на закупку",
        "inventory",
        "Фиксировать потребность склада перед согласованием директором.",
    ),
    (
        "inventory.change_purchase_request",
        "Редактировать заявки на закупку",
        "inventory",
        "Назначать поставщиков, менять позиции и разбивать заявки.",
    ),
    (
        "inventory.approve_purchase_request",
        "Согласовывать заявки на закупку",
        "inventory",
        "Утверждать, отклонять и готовить заявки к отправке поставщикам.",
    ),
)


def add_purchase_request_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")

    permissions = {}
    for codename, name, category, description in NEW_PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            codename=codename,
            defaults={
                "name": name,
                "category": category,
                "description": description,
            },
        )
        permissions[codename] = permission

    for role in Role.objects.filter(code__in=("director", "admin")):
        role.permissions.add(*permissions.values())

    manager = Role.objects.filter(code="manager").first()
    if manager:
        manager.permissions.add(
            permissions["inventory.view_purchase_requests"],
            permissions["inventory.add_purchase_request"],
        )


def remove_purchase_request_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Permission.objects.filter(
        codename__in=[codename for codename, *_ in NEW_PERMISSIONS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_user_can_field_visit"),
    ]

    operations = [
        migrations.RunPython(
            add_purchase_request_permissions,
            reverse_code=remove_purchase_request_permissions,
        ),
    ]
