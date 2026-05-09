from typing import List

from django.db.models import Count
from ninja import Router

from shops.subscription_services import ensure_shop_organization

from .models import ClientPortalIntegration, ClientSyncAction, ClientSyncOrderState
from .schemas import (
    ClientPortalIntegrationSchema,
    ClientPortalIntegrationUpdateSchema,
    ClientSyncRunSchema,
    ClientSyncStatusSchema,
)
from .services import get_or_create_integration, sync_client_service

router = Router(tags=["Синхронизация клиентского сервиса"])


def _current_shop(request):
    shop = getattr(request, "current_shop", None)
    if shop:
        return shop
    return request.auth.get_available_shops().first()


def _integration_for_request(request) -> ClientPortalIntegration:
    shop = _current_shop(request)
    if not shop:
        raise ValueError("Нет доступного филиала")
    organization = ensure_shop_organization(shop)
    return get_or_create_integration(organization)


def _serialize_integration(
    integration: ClientPortalIntegration,
) -> dict:
    return {
        "id": integration.id,
        "organization_id": integration.organization_id,
        "organization_name": integration.organization.name,
        "enabled": integration.enabled,
        "configured": integration.is_configured,
        "base_url": integration.base_url or None,
        "tenant_key": integration.tenant_key or f"org-{integration.organization_id}",
        "client_domain": integration.client_domain or None,
        "auth_policy": integration.auth_policy,
        "support_phone": integration.support_phone or None,
        "support_email": integration.support_email or None,
        "brand_name": integration.brand_name or None,
        "accent_color": integration.accent_color or None,
        "portal_banner_enabled": integration.portal_banner_enabled,
        "portal_banner_title": integration.portal_banner_title or None,
        "portal_banner_subtitle": integration.portal_banner_subtitle or None,
        "portal_banner_image_url": integration.portal_banner_image_url or None,
        "portal_banner_link_url": integration.portal_banner_link_url or None,
        "api_key_configured": bool(integration.api_key),
        "last_push_at": integration.last_push_at.isoformat()
        if integration.last_push_at
        else None,
        "last_pull_at": integration.last_pull_at.isoformat()
        if integration.last_pull_at
        else None,
        "last_error": integration.last_error or None,
    }


@router.get("/status", response=ClientSyncStatusSchema)
def get_client_sync_status(request):
    if not request.auth.has_permission("settings.view_shop"):
        raise PermissionError("Нет прав для просмотра настроек клиентского сервиса")
    integration = _integration_for_request(request)
    order_states = dict(
        ClientSyncOrderState.objects.filter(integration=integration)
        .values("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    actions = dict(
        ClientSyncAction.objects.filter(integration=integration)
        .values("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    return {
        "integration": _serialize_integration(integration),
        "order_states": order_states,
        "actions": actions,
    }


@router.put("/integration", response=ClientPortalIntegrationSchema)
def update_client_sync_integration(
    request,
    data: ClientPortalIntegrationUpdateSchema,
):
    if not request.auth.has_permission("settings.change_shop"):
        raise PermissionError("Нет прав для изменения клиентского сервиса")
    integration = _integration_for_request(request)
    incoming = data.dict(exclude_unset=True)
    for field, value in incoming.items():
        if value is None:
            value = ""
        setattr(integration, field, value)
    if not integration.tenant_key:
        integration.tenant_key = f"org-{integration.organization_id}"
    integration.save()
    return _serialize_integration(integration)


@router.post("/run", response=dict)
def run_client_sync(request, data: ClientSyncRunSchema):
    if not request.auth.has_permission("settings.change_shop"):
        raise PermissionError("Нет прав для запуска синхронизации")
    integration = _integration_for_request(request)
    return sync_client_service(
        integration,
        push=data.push,
        pull=data.pull,
        limit=max(1, min(data.limit, 500)),
    )


@router.get("/actions", response=List[dict])
def list_client_sync_actions(request, limit: int = 50):
    if not request.auth.has_permission("settings.view_shop"):
        raise PermissionError("Нет прав для просмотра действий клиентского сервиса")
    integration = _integration_for_request(request)
    actions = ClientSyncAction.objects.filter(integration=integration).order_by(
        "-received_at"
    )[: max(1, min(limit, 200))]
    return [
        {
            "id": action.id,
            "external_id": action.external_id,
            "action_type": action.action_type,
            "status": action.status,
            "related_order_id": action.related_order_id,
            "related_task_id": action.related_task_id,
            "error_message": action.error_message,
            "received_at": action.received_at,
            "applied_at": action.applied_at,
            "synced_back_at": action.synced_back_at,
        }
        for action in actions
    ]
