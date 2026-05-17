from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from notifications.models import Notification, NotificationType
from users.models import User

from .models import (
    Organization,
    OrganizationSubscription,
    Shop,
    ShopSettings,
    SubscriptionPlan,
)

TRIAL_DAYS = 7
NOTICE_BUCKETS = {30, 20, 10, 0}


def ensure_default_subscription_plans() -> None:
    plans = [
        ("trial", f"Бесплатный период {TRIAL_DAYS} дней", "trial", TRIAL_DAYS, 0),
        ("monthly", "CRM на месяц", "month", 30, 1490),
        ("half_year", "CRM на полгода", "half_year", 182, 7990),
        ("yearly", "CRM на год", "year", 365, 14900),
    ]
    for code, name, period, days, price in plans:
        defaults = {
            "name": name,
            "billing_period": period,
            "duration_days": days,
            "price": price,
            "is_active": True,
        }
        if code == "trial":
            SubscriptionPlan.objects.update_or_create(
                code=code,
                defaults=defaults,
            )
        else:
            SubscriptionPlan.objects.get_or_create(
                code=code,
                defaults=defaults,
            )


def ensure_shop_organization(shop: Shop) -> Organization:
    settings = getattr(shop, "settings", None)
    if settings and settings.organization_id:
        return settings.organization

    with transaction.atomic():
        organization = Organization.objects.create(
            name=shop.name,
            phone=shop.phone,
            email=shop.email,
            address=shop.address[:300],
        )
        if not settings:
            settings = ShopSettings.objects.create(shop=shop)
        settings.organization = organization
        settings.save(update_fields=["organization"])
        return organization


def get_or_create_trial_subscription(
    organization: Organization,
) -> OrganizationSubscription:
    ensure_default_subscription_plans()
    subscription = getattr(organization, "subscription", None)
    if subscription:
        refresh_subscription_status(subscription)
        return subscription

    trial = SubscriptionPlan.objects.get(code="trial")
    now = timezone.now()
    return OrganizationSubscription.objects.create(
        organization=organization,
        plan=trial,
        status=OrganizationSubscription.Status.TRIAL,
        started_at=now,
        expires_at=now + timedelta(days=trial.duration_days),
    )


def change_subscription_plan(
    organization: Organization,
    plan_code: str,
) -> OrganizationSubscription:
    ensure_default_subscription_plans()
    plan = SubscriptionPlan.objects.filter(code=plan_code, is_active=True).first()
    if plan is None:
        raise ValueError("Тариф подписки не найден")
    existing_subscription = getattr(organization, "subscription", None)
    if plan.code == "trial" and existing_subscription:
        raise ValueError("Пробный период нельзя включить повторно")
    now = timezone.now()
    subscription, _ = OrganizationSubscription.objects.update_or_create(
        organization=organization,
        defaults={
            "plan": plan,
            "status": OrganizationSubscription.Status.ACTIVE
            if plan.code != "trial"
            else OrganizationSubscription.Status.TRIAL,
            "started_at": now,
            "expires_at": now + timedelta(days=plan.duration_days),
            "last_notice_bucket": None,
        },
    )
    return subscription


def refresh_subscription_status(
    subscription: OrganizationSubscription,
) -> OrganizationSubscription:
    if subscription.is_expired and subscription.status not in (
        OrganizationSubscription.Status.EXPIRED,
        OrganizationSubscription.Status.CANCELLED,
    ):
        subscription.status = OrganizationSubscription.Status.EXPIRED
        subscription.save(update_fields=["status", "updated_at"])
    return subscription


def serialize_subscription_status(
    subscription: OrganizationSubscription,
) -> dict[str, Any]:
    refresh_subscription_status(subscription)
    return {
        "organization_id": subscription.organization_id,
        "organization_name": subscription.organization.name,
        "plan": subscription.plan,
        "status": subscription.status,
        "status_display": subscription.get_status_display(),
        "started_at": subscription.started_at.isoformat(),
        "expires_at": subscription.expires_at.isoformat(),
        "remaining_days": subscription.remaining_days,
        "remaining_percent": subscription.remaining_percent,
        "color_bucket": subscription.color_bucket,
        "color_hex": subscription.color_hex,
        "is_expired": subscription.is_expired,
    }


def notify_subscription_if_needed(subscription: OrganizationSubscription) -> bool:
    refresh_subscription_status(subscription)
    bucket = subscription.color_bucket
    if bucket not in NOTICE_BUCKETS or subscription.last_notice_bucket == bucket:
        return False

    notification_type, _ = NotificationType.objects.get_or_create(
        code="subscription_expiring",
        defaults={
            "name": "Подписка заканчивается",
            "description": "Уведомления о скором окончании SaaS-подписки",
            "icon": "event_busy",
            "color": "warn",
        },
    )
    users = User.objects.filter(
        shops__settings__organization=subscription.organization,
        is_active=True,
    ).filter(Q(is_superuser=True) | Q(is_director=True) | Q(role__code="admin"))
    users = users.distinct()
    if not users.exists():
        return False

    for user in users:
        Notification.objects.create(
            notification_type=notification_type,
            title="Подписка скоро закончится",
            message=(
                f"У организации {subscription.organization.name} осталось "
                f"{subscription.remaining_days} дн. подписки."
            ),
            recipient=user,
            priority=Notification.Priority.HIGH,
            related_object_type="organization_subscription",
            related_object_id=subscription.id,
            data={
                "remaining_days": subscription.remaining_days,
                "remaining_percent": subscription.remaining_percent,
                "color_bucket": bucket,
            },
            action_url="/admin",
        )

    subscription.last_notice_bucket = bucket
    subscription.save(update_fields=["last_notice_bucket", "updated_at"])
    return True
