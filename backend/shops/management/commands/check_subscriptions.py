from django.core.management.base import BaseCommand

from shops.models import OrganizationSubscription
from shops.subscription_services import (
    notify_subscription_if_needed,
    refresh_subscription_status,
)


class Command(BaseCommand):
    help = "Проверяет подписки организаций и отправляет уведомления об окончании"

    def handle(self, *args, **options):
        checked = 0
        expired = 0
        notified = 0

        subscriptions = OrganizationSubscription.objects.select_related(
            "organization", "plan"
        ).all()
        for subscription in subscriptions.iterator():
            checked += 1
            previous_status = subscription.status
            refresh_subscription_status(subscription)
            subscription.refresh_from_db(fields=["status", "last_notice_bucket"])
            if previous_status != subscription.status:
                expired += 1
            if notify_subscription_if_needed(subscription):
                notified += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Проверено подписок: {checked}; истекло: {expired}; "
                f"уведомления отправлены: {notified}"
            )
        )
