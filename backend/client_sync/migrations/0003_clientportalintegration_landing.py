from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("client_sync", "0002_clientportalintegration_portal_banner"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientportalintegration",
            name="landing_section_eyebrow",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="Лендинг: подзаголовок секции карточек",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="landing_section_title",
            field=models.CharField(
                blank=True,
                max_length=200,
                verbose_name="Лендинг: заголовок секции карточек",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="landing_section_subtitle",
            field=models.TextField(
                blank=True,
                verbose_name="Лендинг: текст под заголовком секции",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="landing_feature_cards",
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name="Лендинг: карточки (до 4 шт.)",
            ),
        ),
        migrations.AddField(
            model_name="clientportalintegration",
            name="landing_promo_spotlight",
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name="Лендинг: акцентная карточка / призыв",
            ),
        ),
    ]
