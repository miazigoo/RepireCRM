"""Add Shop.city for landing city filter."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shops", "0004_shopsettings_field_visit"),
    ]

    operations = [
        migrations.AddField(
            model_name="shop",
            name="city",
            field=models.CharField(
                blank=True,
                help_text="Для фильтра на лендинге; если пусто — берём из начала адреса",
                max_length=100,
                verbose_name="Город",
            ),
        ),
    ]
