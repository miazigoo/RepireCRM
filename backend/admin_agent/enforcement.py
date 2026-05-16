from __future__ import annotations

from datetime import timedelta
from datetime import timezone as datetime_timezone
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.utils import timezone
from ninja.errors import HttpError

from .models import AdminServiceState

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
GATE_STATE_CACHE_KEY = "admin_agent:subscription_gate_state"
GATE_STATE_CACHE_TTL = 60

EXEMPT_PATH_PREFIXES = (
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/profile",
    "/api/auth/change-password",
    "/api/auth/switch-shop",
    "/api/admin-agent",
    "/api/notifications",
    "/api/shops/subscription",
    "/api/health",
    "/api/docs",
)


def enforce_admin_subscription(request, user) -> None:
    if not getattr(settings, "ADMIN_SERVICE_ENFORCEMENT_ENABLED", False):
        return
    if not _admin_service_configured():
        return
    if request.method.upper() not in MUTATING_METHODS:
        return
    if _is_exempt_path(request.path):
        return
    if getattr(user, "is_superuser", False) and getattr(
        settings, "ADMIN_SERVICE_ENFORCEMENT_ALLOW_SUPERUSER_BYPASS", True
    ):
        return

    state = subscription_gate_state()
    reason = subscription_denial_reason(state)
    if reason:
        raise HttpError(402, reason)


def subscription_gate_state() -> dict[str, Any]:
    cached = cache.get(GATE_STATE_CACHE_KEY)
    if cached is not None:
        return cached

    try:
        state = AdminServiceState.objects.filter(
            key=AdminServiceState.DEFAULT_KEY
        ).first()
    except DatabaseError:
        return {"available": False, "storage_error": True}

    if not state:
        payload = {"available": False}
    else:
        payload = {
            "available": True,
            "subscription": state.subscription or {},
            "last_synced_at": state.last_synced_at,
            "last_error_message": state.last_error_message,
        }
    cache.set(GATE_STATE_CACHE_KEY, payload, GATE_STATE_CACHE_TTL)
    return payload


def subscription_denial_reason(state: dict[str, Any]) -> str | None:
    if state.get("storage_error"):
        return None

    last_synced_at = state.get("last_synced_at")
    if not last_synced_at:
        if getattr(settings, "ADMIN_SERVICE_ENFORCEMENT_REQUIRE_SYNC", False):
            return "Подписка RepireCRM еще не подтверждена центральной админкой"
        return None

    if _is_state_stale(last_synced_at):
        hours = getattr(settings, "ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS", 72)
        return (
            "Подписка RepireCRM не подтверждалась слишком долго. "
            f"Проверьте связь с центральной админкой, grace-период {hours} ч."
        )

    subscription = state.get("subscription") or {}
    access_allowed = subscription.get("access_allowed")
    if access_allowed is False:
        status = subscription.get("status") or "unknown"
        reason = subscription.get("reason") or status
        return (
            "Доступ к коммерческим операциям ограничен: "
            f"подписка {status}, причина {reason}. "
            "Откройте Администрирование -> Подписка и поддержка."
        )

    return None


def enforcement_snapshot() -> dict[str, Any]:
    return {
        "enabled": getattr(settings, "ADMIN_SERVICE_ENFORCEMENT_ENABLED", False),
        "require_sync": getattr(
            settings, "ADMIN_SERVICE_ENFORCEMENT_REQUIRE_SYNC", False
        ),
        "stale_grace_hours": getattr(
            settings, "ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS", 72
        ),
        "superuser_bypass": getattr(
            settings, "ADMIN_SERVICE_ENFORCEMENT_ALLOW_SUPERUSER_BYPASS", True
        ),
    }


def _admin_service_configured() -> bool:
    return bool(settings.ADMIN_SERVICE_URL and settings.ADMIN_SERVICE_AGENT_TOKEN)


def _is_exempt_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES)


def _is_state_stale(last_synced_at) -> bool:
    if timezone.is_naive(last_synced_at):
        last_synced_at = timezone.make_aware(last_synced_at, datetime_timezone.utc)
    hours = getattr(settings, "ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS", 72)
    return timezone.now() - last_synced_at > timedelta(hours=hours)
