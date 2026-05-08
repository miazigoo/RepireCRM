from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="permission",
            name="category",
            field=models.CharField(
                choices=[
                    ("orders", "Заказы"),
                    ("customers", "Клиенты"),
                    ("inventory", "Склад"),
                    ("reports", "Отчеты"),
                    ("tasks", "Задачи"),
                    ("finance", "Финансы"),
                    ("settings", "Настройки"),
                    ("users", "Пользователи"),
                ],
                max_length=20,
                verbose_name="Категория",
            ),
        ),
    ]
