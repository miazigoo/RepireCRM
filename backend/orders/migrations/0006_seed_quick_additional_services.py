from decimal import Decimal

from django.db import migrations


def seed_quick_additional_services(apps, schema_editor):
    AdditionalService = apps.get_model("orders", "AdditionalService")
    defaults = [
        {
            "name": "Чехол",
            "category": "accessories",
            "description": "Быстрое добавление защитного чехла к заказу",
            "price": Decimal("1500.00"),
        },
        {
            "name": "Защитное стекло",
            "category": "protection",
            "description": "Наклейка защитного стекла на экран",
            "price": Decimal("500.00"),
        },
    ]

    for item in defaults:
        service, created = AdditionalService.objects.get_or_create(
            name=item["name"],
            defaults={
                "category": item["category"],
                "description": item["description"],
                "price": item["price"],
                "is_active": True,
            },
        )
        if not created and not service.is_active:
            service.is_active = True
            service.save(update_fields=["is_active"])


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_alter_orderauditlog_action_orderapproval"),
    ]

    operations = [
        migrations.RunPython(seed_quick_additional_services, migrations.RunPython.noop),
    ]
