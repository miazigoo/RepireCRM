from celery import shared_task

from .models import ClientPortalIntegration
from .services import sync_client_portal


@shared_task(name="client_sync.tasks.sync_client_portals")
def sync_client_portals(limit: int = 100):
    result = {"integrations": 0, "pushed": 0, "pulled": 0, "applied": 0, "errors": 0}
    integrations = ClientPortalIntegration.objects.filter(
        enabled=True,
        base_url__gt="",
        api_key__gt="",
    )
    for integration in integrations:
        current = sync_client_portal(integration, limit=limit)
        result["integrations"] += 1
        result["pushed"] += current.get("pushed", 0)
        result["pulled"] += current.get("pulled", 0)
        result["applied"] += current.get("applied", 0)
        result["errors"] += current.get("errors", 0)
    return result
