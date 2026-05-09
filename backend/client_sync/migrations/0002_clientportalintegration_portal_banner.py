from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("client_sync", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientportalintegration",
            name="portal_banner_enabled",
            field=models.BooleanField(
                default=False,
                verbose_name="Показывать рекламный баннер в клиентском кабинете",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="portal_banner_title",
            field=models.CharField(
                blank=True,
                max_length=200,
                verbose_name="Заголовок баннера",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="portal_banner_subtitle",
            field=models.CharField(
                blank=True,
                max_length=500,
                verbose_name="Подзаголовок баннера",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="portal_banner_image_url",
            field=models.URLField(
                blank=True,
                verbose_name="Картинка баннера (URL)",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="portal_banner_link_url",
            field=models.URLField(
                blank=True,
                verbose_name="Ссылка при клике на баннер",
            ),
        ),
    ]
