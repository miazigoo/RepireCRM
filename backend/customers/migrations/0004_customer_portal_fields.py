from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0003_customer_marketing_consent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="portal_is_active",
            field=models.BooleanField(default=False, verbose_name="Кабинет активен"),
        ),
        migrations.AddField(
            model_name="customer",
            name="portal_last_login_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Последний вход в кабинет"
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="portal_password",
            field=models.CharField(
                blank=True, max_length=128, verbose_name="Пароль кабинета"
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="portal_registered_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Дата регистрации в кабинете"
            ),
        ),
    ]
