"""Add shop coordinates for public landing maps."""

import decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shops", "0005_shop_city"),
    ]

    operations = [
        migrations.AddField(
            model_name="shop",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text="Координата точки для карты клиентского лендинга",
                max_digits=9,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(decimal.Decimal("-90")),
                    django.core.validators.MaxValueValidator(decimal.Decimal("90")),
                ],
                verbose_name="Широта",
            ),
        ),
        migrations.AddField(
            model_name="shop",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text="Координата точки для карты клиентского лендинга",
                max_digits=9,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(decimal.Decimal("-180")),
                    django.core.validators.MaxValueValidator(decimal.Decimal("180")),
                ],
                verbose_name="Долгота",
            ),
        ),
    ]
