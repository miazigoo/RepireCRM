from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="is_paid",
            field=models.BooleanField(
                default=False, verbose_name="Оплачиваемая задача"
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="kind",
            field=models.CharField(
                choices=[
                    ("regular", "Обычная"),
                    ("urgent", "Срочная"),
                    ("global", "Глобальная"),
                    ("planned", "Плановая"),
                ],
                default="regular",
                max_length=12,
                verbose_name="Тип задачи",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="payment_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0"),
                max_digits=10,
                verbose_name="Оплата за задачу",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="substatus",
            field=models.CharField(
                choices=[
                    ("new", "Новая"),
                    ("accepted", "Принята"),
                    ("waiting", "Ожидает"),
                    ("blocked", "Заблокирована"),
                    ("review", "На проверке"),
                    ("done", "Готово"),
                ],
                default="new",
                max_length=20,
                verbose_name="Подстатус",
            ),
        ),
    ]
