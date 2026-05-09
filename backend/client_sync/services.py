from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from customers.models import Customer, CustomerShopHistory
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order, OrderApproval, OrderAuditLog
from shops.models import Organization, Shop
from tasks.models import Task, TaskCategory

from .models import ClientPortalIntegration, ClientSyncAction, ClientSyncOrderState

SYNC_USER_USERNAME = "client-sync"
CLIENT_ACTION_CATEGORY = "Клиентский кабинет"
DEFAULT_TIMEOUT_SECONDS = 20


@dataclass
class SyncResult:
    pushed: int = 0
    skipped: int = 0
    pulled: int = 0
    applied: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "pushed": self.pushed,
            "skipped": self.skipped,
            "pulled": self.pulled,
            "applied": self.applied,
            "errors": self.errors,
        }


class ClientSyncError(RuntimeError):
    pass


def get_or_create_integration(
    organization: Organization,
) -> ClientPortalIntegration:
    integration, _ = ClientPortalIntegration.objects.get_or_create(
        organization=organization,
        defaults={
            "tenant_key": f"org-{organization.id}",
            "brand_name": organization.name,
            "support_phone": organization.phone,
            "support_email": organization.email,
        },
    )
    return integration


def organization_shops(organization: Organization):
    return Shop.objects.filter(settings__organization=organization, is_active=True)


def integration_headers(integration: ClientPortalIntegration) -> dict[str, str]:
    return {
        "X-Sync-Token": integration.api_key,
        "X-Tenant-Key": integration.tenant_key or f"org-{integration.organization_id}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def build_sync_url(integration: ClientPortalIntegration, path: str) -> str:
    base_url = integration.base_url.rstrip("/") + "/"
    return urljoin(base_url, path.lstrip("/"))


def serialize_money(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def serialize_datetime(value) -> str | None:
    return value.isoformat() if value else None


def serialize_customer(customer: Customer) -> dict[str, Any]:
    return {
        "crm_customer_id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "middle_name": customer.middle_name,
        "full_name": customer.full_name,
        "phone": str(customer.phone) if customer.phone else "",
        "email": customer.email or "",
        "preferred_channel": customer.preferred_channel,
        "marketing_consent": customer.marketing_consent,
        "created_at": serialize_datetime(customer.created_at),
        "updated_at": serialize_datetime(customer.updated_at),
    }


def serialize_order_snapshot(order: Order) -> dict[str, Any]:
    device = order.device
    model = device.model
    organization = getattr(getattr(order.shop, "settings", None), "organization", None)
    return {
        "crm_order_id": order.id,
        "order_number": order.order_number,
        "organization": {
            "crm_organization_id": organization.id if organization else None,
            "name": organization.name if organization else "",
        },
        "shop": {
            "crm_shop_id": order.shop_id,
            "code": order.shop.code,
            "name": order.shop.name,
            "phone": order.shop.phone,
            "email": order.shop.email,
            "address": order.shop.address,
        },
        "customer": serialize_customer(order.customer),
        "device": {
            "crm_device_id": device.id,
            "device_type": model.device_type.name if model.device_type else "",
            "brand": model.brand.name,
            "model_name": model.name,
            "serial_number": device.serial_number,
            "imei": device.imei,
            "color": device.color,
            "storage_capacity": device.storage_capacity,
        },
        "status": order.status,
        "status_display": order.get_status_display(),
        "priority": order.priority,
        "problem_description": order.problem_description,
        "diagnosis": order.diagnosis or "",
        "work_description": order.work_description or "",
        "accessories": order.accessories or "",
        "device_condition": order.device_condition or "",
        "cost_estimate": serialize_money(order.cost_estimate),
        "final_cost": serialize_money(order.final_cost),
        "prepayment": serialize_money(order.prepayment),
        "total_cost": serialize_money(order.total_cost),
        "remaining_payment": serialize_money(order.remaining_payment),
        "warranty_days": order.warranty_days,
        "warranty_until": serialize_datetime(order.warranty_until),
        "warranty_active": bool(order.warranty_active),
        "is_warranty_case": order.is_warranty_case,
        "warranty_parent_order_id": order.warranty_parent_id,
        "warranty_parent_order_number": (
            order.warranty_parent.order_number if order.warranty_parent else ""
        ),
        "warranty_reason": order.warranty_reason,
        "created_at": serialize_datetime(order.created_at),
        "updated_at": serialize_datetime(order.updated_at),
        "estimated_completion": serialize_datetime(order.estimated_completion),
        "completed_at": serialize_datetime(order.completed_at),
        "repair_stages": [
            {
                "crm_stage_id": stage.id,
                "title": stage.title,
                "description": stage.description,
                "photo_url": stage.photo_url,
                "position": stage.position,
                "created_at": serialize_datetime(stage.created_at),
                "updated_at": serialize_datetime(stage.updated_at),
            }
            for stage in order.repair_stages.filter(customer_visible=True)
        ],
        "approvals": [
            {
                "crm_approval_id": approval.id,
                "title": approval.title,
                "description": approval.description,
                "amount": serialize_money(approval.amount),
                "status": approval.status,
                "customer_comment": approval.customer_comment,
                "decided_at": serialize_datetime(approval.decided_at),
                "created_at": serialize_datetime(approval.created_at),
                "updated_at": serialize_datetime(approval.updated_at),
            }
            for approval in order.approvals.all()
        ],
        "additional_services": [
            {
                "crm_service_id": service.service_id,
                "name": service.service.name,
                "category": service.service.category,
                "quantity": service.quantity,
                "price": serialize_money(service.price),
                "total_price": serialize_money(service.total_price),
            }
            for service in order.orderservice_set.all()
        ],
    }


def payload_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def orders_for_push(integration: ClientPortalIntegration, limit: int = 100):
    shops = organization_shops(integration.organization)
    pending_ids = ClientSyncOrderState.objects.filter(
        integration=integration,
        status__in=[
            ClientSyncOrderState.Status.PENDING,
            ClientSyncOrderState.Status.ERROR,
        ],
    ).values_list("order_id", flat=True)
    queryset = Order.objects.filter(shop__in=shops)
    if integration.last_push_at:
        queryset = queryset.filter(
            Q(id__in=pending_ids) | Q(updated_at__gte=integration.last_push_at)
        )
    return (
        queryset.select_related(
            "shop",
            "shop__settings",
            "shop__settings__organization",
            "customer",
            "device__model__brand",
            "device__model__device_type",
            "warranty_parent",
        )
        .prefetch_related("repair_stages", "approvals", "orderservice_set__service")
        .distinct()
        .order_by("updated_at")[:limit]
    )


def push_order_snapshots(
    integration: ClientPortalIntegration,
    limit: int = 100,
    session: requests.Session | None = None,
) -> SyncResult:
    result = SyncResult()
    if not integration.is_configured:
        return result

    session = session or requests.Session()
    orders = list(orders_for_push(integration, limit=limit))
    if not orders:
        integration.last_push_at = timezone.now()
        integration.last_error = ""
        integration.save(update_fields=["last_push_at", "last_error", "updated_at"])
        return result

    snapshots: list[dict[str, Any]] = []
    states: dict[int, tuple[ClientSyncOrderState, str]] = {}
    for order in orders:
        snapshot = serialize_order_snapshot(order)
        current_hash = payload_hash(snapshot)
        state, _ = ClientSyncOrderState.objects.get_or_create(
            integration=integration,
            order=order,
        )
        if state.status == ClientSyncOrderState.Status.SYNCED and (
            state.payload_hash == current_hash
        ):
            result.skipped += 1
            continue
        snapshots.append(snapshot)
        states[order.id] = (state, current_hash)

    if not snapshots:
        integration.last_push_at = timezone.now()
        integration.last_error = ""
        integration.save(update_fields=["last_push_at", "last_error", "updated_at"])
        return result

    response = session.post(
        build_sync_url(integration, "/api/sync/orders/upsert"),
        headers=integration_headers(integration),
        json={
            "tenant_key": integration.tenant_key,
            "sent_at": serialize_datetime(timezone.now()),
            "orders": snapshots,
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        message = response.text[:1000]
        for state, _ in states.values():
            state.status = ClientSyncOrderState.Status.ERROR
            state.attempts += 1
            state.last_error = message
            state.save(update_fields=["status", "attempts", "last_error", "updated_at"])
        integration.last_error = message
        integration.save(update_fields=["last_error", "updated_at"])
        result.errors += len(states)
        return result

    payload = _response_json(response)
    response_items = _response_items(payload, keys=("orders", "items"))
    remote_ids = {
        int(item["crm_order_id"]): str(item.get("remote_order_id") or "")
        for item in response_items
        if item.get("crm_order_id")
    }
    now = timezone.now()
    for snapshot in snapshots:
        order_id = int(snapshot["crm_order_id"])
        state, current_hash = states[order_id]
        state.status = ClientSyncOrderState.Status.SYNCED
        state.payload_hash = current_hash
        state.remote_order_id = remote_ids.get(order_id, state.remote_order_id)
        state.last_error = ""
        state.last_synced_at = now
        state.attempts += 1
        state.save(
            update_fields=[
                "status",
                "payload_hash",
                "remote_order_id",
                "last_error",
                "last_synced_at",
                "attempts",
                "updated_at",
            ]
        )
        result.pushed += 1

    integration.last_push_at = now
    integration.last_error = ""
    integration.save(update_fields=["last_push_at", "last_error", "updated_at"])
    return result


def pull_pending_actions(
    integration: ClientPortalIntegration,
    limit: int = 100,
    session: requests.Session | None = None,
) -> SyncResult:
    result = SyncResult()
    if not integration.is_configured:
        return result

    session = session or requests.Session()
    response = session.get(
        build_sync_url(integration, "/api/sync/actions"),
        headers=integration_headers(integration),
        params={"limit": limit},
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        integration.last_error = response.text[:1000]
        integration.save(update_fields=["last_error", "updated_at"])
        result.errors += 1
        return result

    payload = _response_json(response)
    for raw_action in _response_items(payload, keys=("actions", "items")):
        result.pulled += 1
        action = record_action(integration, raw_action)
        if action.status == ClientSyncAction.Status.RECEIVED:
            apply_client_action(action)
        if action.status in (
            ClientSyncAction.Status.APPLIED,
            ClientSyncAction.Status.REJECTED,
            ClientSyncAction.Status.ERROR,
        ):
            mark_action_synced(integration, action, session=session)
        if action.status == ClientSyncAction.Status.APPLIED:
            result.applied += 1
        elif action.status == ClientSyncAction.Status.ERROR:
            result.errors += 1

    integration.last_pull_at = timezone.now()
    integration.last_error = ""
    integration.save(update_fields=["last_pull_at", "last_error", "updated_at"])
    return result


def sync_client_portal(
    integration: ClientPortalIntegration,
    push: bool = True,
    pull: bool = True,
    limit: int = 100,
) -> dict[str, int]:
    result = SyncResult()
    if push:
        push_result = push_order_snapshots(integration, limit=limit)
        result.pushed += push_result.pushed
        result.skipped += push_result.skipped
        result.errors += push_result.errors
    if pull:
        pull_result = pull_pending_actions(integration, limit=limit)
        result.pulled += pull_result.pulled
        result.applied += pull_result.applied
        result.errors += pull_result.errors
    return result.as_dict()


def record_action(
    integration: ClientPortalIntegration,
    raw_action: dict[str, Any],
) -> ClientSyncAction:
    external_id = str(raw_action.get("id") or raw_action.get("external_id") or "")
    action_type = str(raw_action.get("type") or raw_action.get("action_type") or "")
    if not external_id or not action_type:
        raise ClientSyncError("Client action must include id and type")

    action, created = ClientSyncAction.objects.get_or_create(
        integration=integration,
        external_id=external_id,
        defaults={
            "action_type": action_type,
            "payload": raw_action.get("payload") or raw_action,
        },
    )
    if not created and action.status == ClientSyncAction.Status.RECEIVED:
        action.action_type = action_type
        action.payload = raw_action.get("payload") or raw_action
        action.save(update_fields=["action_type", "payload"])
    return action


def apply_client_action(action: ClientSyncAction) -> ClientSyncAction:
    try:
        if action.action_type in {"approval.decided", "approval_decided"}:
            _apply_approval_decision(action)
        elif action.action_type in {"repair_request.created", "order.created"}:
            _apply_repair_request(action)
        else:
            _create_task_from_action(action, title_prefix="Действие клиента")
        action.status = ClientSyncAction.Status.APPLIED
        action.error_message = ""
        action.applied_at = timezone.now()
        action.save(
            update_fields=[
                "status",
                "error_message",
                "applied_at",
                "related_order",
                "related_task",
            ]
        )
    except Exception as exc:
        action.status = ClientSyncAction.Status.ERROR
        action.error_message = str(exc)
        action.save(update_fields=["status", "error_message"])
    return action


def mark_action_synced(
    integration: ClientPortalIntegration,
    action: ClientSyncAction,
    session: requests.Session | None = None,
) -> None:
    if action.synced_back_at:
        return
    session = session or requests.Session()
    response = session.post(
        build_sync_url(
            integration, f"/api/sync/actions/{action.external_id}/mark-synced"
        ),
        headers=integration_headers(integration),
        json={
            "status": action.status,
            "crm_order_id": action.related_order_id,
            "crm_task_id": action.related_task_id,
            "error": action.error_message,
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        action.error_message = response.text[:1000]
        action.save(update_fields=["error_message"])
        return
    action.synced_back_at = timezone.now()
    action.save(update_fields=["synced_back_at"])


def _apply_approval_decision(action: ClientSyncAction) -> None:
    payload = action.payload
    approval_id = (
        payload.get("crm_approval_id")
        or payload.get("approval_id")
        or (payload.get("approval") or {}).get("crm_approval_id")
    )
    if not approval_id:
        raise ClientSyncError("approval.decided requires crm_approval_id")
    status = payload.get("status") or payload.get("decision")
    if status not in {
        OrderApproval.StatusChoices.APPROVED,
        OrderApproval.StatusChoices.REJECTED,
    }:
        raise ClientSyncError("approval.decided status must be approved or rejected")

    approval = OrderApproval.objects.select_related("order").get(id=approval_id)
    if approval.status != OrderApproval.StatusChoices.PENDING:
        action.related_order = approval.order
        return
    approval.status = status
    approval.customer_comment = payload.get("comment") or payload.get("message") or ""
    approval.decided_at = timezone.now()
    approval.save(
        update_fields=["status", "customer_comment", "decided_at", "updated_at"]
    )
    action.related_order = approval.order
    OrderAuditLog.objects.create(
        order=approval.order,
        action=OrderAuditLog.ActionChoices.APPROVAL_DECIDED,
        message="Клиент ответил на согласование через внешний кабинет",
        changes={
            "approval_id": approval.id,
            "status": status,
            "external_action_id": action.external_id,
            "customer_comment": approval.customer_comment,
        },
    )
    if status == OrderApproval.StatusChoices.APPROVED:
        order = approval.order
        order.cost_estimate = approval.amount
        order.save(update_fields=["cost_estimate", "updated_at"])


def _apply_repair_request(action: ClientSyncAction) -> None:
    payload = action.payload
    shop = _shop_from_payload(action.integration.organization, payload)
    customer = _customer_from_payload(payload)
    if not customer:
        action.related_task = _create_task_from_action(
            action,
            title_prefix="Заявка клиента требует проверки контакта",
            shop=shop,
        )
        return

    with transaction.atomic():
        device_payload = payload.get("device") or {}
        order_payload = payload.get("order") or payload
        brand_name = (device_payload.get("brand") or payload.get("brand") or "").strip()
        model_name = (
            device_payload.get("model_name") or payload.get("model_name") or ""
        ).strip()
        device_type_name = (
            device_payload.get("device_type")
            or payload.get("device_type")
            or "Смартфон"
        ).strip()
        if not brand_name or not model_name:
            raise ClientSyncError(
                "repair_request.created requires brand and model_name"
            )

        brand, _ = DeviceBrand.objects.get_or_create(name=brand_name)
        device_type, _ = DeviceType.objects.get_or_create(name=device_type_name)
        model, _ = DeviceModel.objects.get_or_create(
            brand=brand,
            device_type=device_type,
            name=model_name,
        )
        device = Device.objects.create(
            model=model,
            serial_number=device_payload.get("serial_number") or "",
            imei=device_payload.get("imei") or "",
            color=device_payload.get("color") or "",
            storage_capacity=device_payload.get("storage_capacity") or "",
        )
        order = Order.objects.create(
            shop=shop,
            customer=customer,
            device=device,
            problem_description=(
                order_payload.get("problem_description")
                or payload.get("problem_description")
                or "Заявка клиента из внешнего кабинета"
            ),
            accessories=order_payload.get("accessories") or "",
            device_condition=order_payload.get("device_condition") or "",
            cost_estimate=Decimal(str(order_payload.get("cost_estimate") or "0")),
            created_by=_sync_user(shop),
            notes=f"Заявка клиента из внешнего кабинета. Action: {action.external_id}",
        )
        CustomerShopHistory.objects.get_or_create(customer=customer, shop=shop)
        customer.update_statistics()
        action.related_order = order
        OrderAuditLog.objects.create(
            order=order,
            action=OrderAuditLog.ActionChoices.CREATED,
            message="Заказ создан из внешнего клиентского кабинета",
            changes={"external_action_id": action.external_id},
        )


def _customer_from_payload(payload: dict[str, Any]) -> Customer | None:
    customer_payload = payload.get("customer") or {}
    phone = customer_payload.get("phone") or payload.get("phone") or ""
    email = customer_payload.get("email") or payload.get("email") or ""
    if phone:
        customer = Customer.objects.filter(phone=phone).first()
        if customer:
            return customer
        return Customer.objects.create(
            first_name=customer_payload.get("first_name") or "Клиент",
            last_name=customer_payload.get("last_name") or "из кабинета",
            middle_name=customer_payload.get("middle_name") or "",
            phone=phone,
            email=email or "",
            source=Customer.CustomerSource.WEBSITE,
            source_details="external-client-portal",
            marketing_consent=bool(customer_payload.get("marketing_consent", False)),
        )
    if email:
        return Customer.objects.filter(email=email).first()
    return None


def _shop_from_payload(organization: Organization, payload: dict[str, Any]) -> Shop:
    shop_payload = payload.get("shop") or {}
    shop_code = shop_payload.get("code") or payload.get("shop_code")
    shops = organization_shops(organization)
    if shop_code:
        shop = shops.filter(code=shop_code).first()
        if shop:
            return shop
    shop = shops.first()
    if not shop:
        raise ClientSyncError("No active shop linked to client portal organization")
    return shop


def _create_task_from_action(
    action: ClientSyncAction,
    title_prefix: str,
    shop: Shop | None = None,
) -> Task:
    shop = shop or _shop_from_payload(action.integration.organization, action.payload)
    category, _ = TaskCategory.objects.get_or_create(
        name=CLIENT_ACTION_CATEGORY,
        defaults={
            "description": "Автоматические задачи из клиентского кабинета",
            "color": "#0f62fe",
            "icon": "support_agent",
        },
    )
    order = _order_from_payload(action.payload)
    task = Task.objects.create(
        title=f"{title_prefix}: {action.action_type}",
        description=json.dumps(action.payload, ensure_ascii=False, indent=2),
        category=category,
        priority=Task.Priority.NORMAL,
        kind=Task.TaskKind.REGULAR,
        status=Task.Status.PENDING,
        substatus=Task.Substatus.NEW,
        assignment_type=Task.AssignmentType.SHOP,
        assigned_shop=shop,
        related_order=order,
        related_customer=order.customer if order else None,
        created_by=_sync_user(shop),
    )
    action.related_task = task
    if order:
        action.related_order = order
    return task


def _order_from_payload(payload: dict[str, Any]) -> Order | None:
    order_id = payload.get("crm_order_id") or payload.get("order_id")
    order_number = payload.get("order_number")
    queryset = Order.objects.all()
    if order_id:
        return queryset.filter(id=order_id).first()
    if order_number:
        return queryset.filter(order_number=order_number).first()
    return None


def _sync_user(shop: Shop):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username=SYNC_USER_USERNAME,
        defaults={
            "first_name": "Client",
            "last_name": "Sync",
            "email": "client-sync@repair-crm.local",
            "is_active": False,
        },
    )
    if user.current_shop_id != shop.id:
        user.current_shop = shop
        user.save(update_fields=["current_shop"])
    user.shops.add(shop)
    return user


def _response_json(response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {}


def _response_items(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []
