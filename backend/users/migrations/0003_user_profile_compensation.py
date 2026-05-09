from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_expand_permission_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="bio",
            field=models.TextField(blank=True, verbose_name="Описание профиля"),
        ),
        migrations.AddField(
            model_name="user",
            name="compensation_type",
            field=models.CharField(
                choices=[
                    ("fixed", "Фикс за заказ"),
                    ("commission", "Процент"),
                    ("mixed", "Фикс + процент"),
                ],
                default="fixed",
                max_length=20,
                verbose_name="Схема оплаты",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="fixed_order_payment",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=10,
                verbose_name="Фиксированная оплата за заказ",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="product_commission_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=5,
                verbose_name="Процент с продаж товаров",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_status",
            field=models.CharField(
                blank=True, max_length=120, verbose_name="Статус профиля"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="service_commission_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=5,
                verbose_name="Процент с услуг",
            ),
        ),
    ]
