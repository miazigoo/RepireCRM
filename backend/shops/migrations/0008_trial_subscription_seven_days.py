from datetime import timedelta

from django.db import migrations


TRIAL_DAYS = 7


def apply_trial_period(apps, schema_editor):
    SubscriptionPlan = apps.get_model("shops", "SubscriptionPlan")
    OrganizationSubscription = apps.get_model("shops", "OrganizationSubscription")

    trial_plan, _ = SubscriptionPlan.objects.update_or_create(
        code="trial",
        defaults={
            "name": f"Бесплатный период {TRIAL_DAYS} дней",
            "billing_period": "trial",
            "duration_days": TRIAL_DAYS,
            "price": 0,
            "is_active": True,
        },
    )

    trial_subscriptions = OrganizationSubscription.objects.filter(
        plan=trial_plan,
        status="trial",
    )
    for subscription in trial_subscriptions.iterator():
        capped_expires_at = subscription.started_at + timedelta(days=TRIAL_DAYS)
        if subscription.expires_at <= capped_expires_at:
            continue
        subscription.expires_at = capped_expires_at
        subscription.last_notice_bucket = None
        subscription.save(
            update_fields=["expires_at", "last_notice_bucket", "updated_at"]
        )


def revert_trial_period(apps, schema_editor):
    SubscriptionPlan = apps.get_model("shops", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(code="trial").update(
        name="Бесплатный период 45 дней",
        duration_days=45,
        price=0,
        is_active=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("shops", "0007_shopsettings_default_goods_vat_code_and_more"),
    ]

    operations = [
        migrations.RunPython(apply_trial_period, revert_trial_period),
    ]
