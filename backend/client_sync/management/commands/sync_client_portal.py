from django.core.management.base import BaseCommand

from client_sync.models import ClientPortalIntegration
from client_sync.services import sync_client_portal


class Command(BaseCommand):
    help = "Синхронизировать CRM с внешним клиентским backend."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", type=int)
        parser.add_argument("--push-only", action="store_true")
        parser.add_argument("--pull-only", action="store_true")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        queryset = ClientPortalIntegration.objects.filter(
            enabled=True,
            base_url__gt="",
            api_key__gt="",
        ).select_related("organization")
        if options.get("organization_id"):
            queryset = queryset.filter(organization_id=options["organization_id"])

        push = not options["pull_only"]
        pull = not options["push_only"]
        total = {"integrations": 0, "pushed": 0, "pulled": 0, "applied": 0, "errors": 0}
        for integration in queryset:
            result = sync_client_portal(
                integration,
                push=push,
                pull=pull,
                limit=max(1, min(options["limit"], 500)),
            )
            total["integrations"] += 1
            for key in ("pushed", "pulled", "applied", "errors"):
                total[key] += result.get(key, 0)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{integration.organization}: pushed={result.get('pushed', 0)} "
                    f"pulled={result.get('pulled', 0)} "
                    f"applied={result.get('applied', 0)} "
                    f"errors={result.get('errors', 0)}"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Done: {total}"))
