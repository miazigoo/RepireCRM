from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timezone as datetime_timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .enforcement import enforcement_snapshot
from .models import AdminServiceState

logger = logging.getLogger("repair_crm")

LAST_RESPONSE_CACHE_KEY = "admin_agent:last_response"
LAST_ERROR_CACHE_KEY = "admin_agent:last_error"
LAST_SUBSCRIPTION_CACHE_KEY = "admin_agent:last_subscription"
CACHE_TTL_SECONDS = 60 * 60 * 24


class AdminAgentError(RuntimeError):
    pass


@dataclass
class AdminAgentService:
    session: requests.Session | None = None

    def is_configured(self) -> bool:
        return bool(settings.ADMIN_SERVICE_URL and settings.ADMIN_SERVICE_AGENT_TOKEN)

    def api_url(self, path: str) -> str:
        return urljoin(settings.ADMIN_SERVICE_URL.rstrip("/") + "/", path.lstrip("/"))

    def heartbeat_url(self) -> str:
        return self.api_url("api/agent/heartbeat")

    def build_payload(self) -> dict[str, Any]:
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        from customers.models import Customer
        from finance.models import Payment
        from orders.models import Order
        from shops.models import Shop

        User = get_user_model()
        revenue = Payment.objects.filter(
            payment_type=Payment.PaymentType.INCOME,
            status=Payment.PaymentStatus.COMPLETED,
            payment_date__gte=month_start,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        return {
            "version": settings.APP_VERSION or None,
            "environment": settings.ENVIRONMENT,
            "health_status": "ok",
            "metrics": {
                "active_users": User.objects.filter(is_active=True).count(),
                "shops_count": Shop.objects.filter(is_active=True).count(),
                "orders_total": Order.objects.count(),
                "orders_month": Order.objects.filter(
                    created_at__gte=month_start
                ).count(),
                "customers_total": Customer.objects.count(),
                "portal_users_total": 0,
                "revenue_month": int(revenue * 100),
                "extra": {
                    "debug": settings.DEBUG,
                    "database_engine": settings.DATABASES["default"]["ENGINE"],
                },
            },
            "payload": {
                "backend_public_url": settings.BACKEND_PUBLIC_URL,
                "frontend_url": settings.FRONTEND_URL,
                "timestamp": now.isoformat(),
            },
        }

    def send_heartbeat(self, force: bool = False) -> dict[str, Any]:
        if not force and not settings.ADMIN_SERVICE_HEARTBEAT_ENABLED:
            return {"status": "skipped", "reason": "disabled"}
        if not self.is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        try:
            payload = self._post("api/agent/heartbeat", self.build_payload())
        except AdminAgentError as exc:
            message = str(exc)
            logger.warning("Admin heartbeat failed: %s", message)
            self._store_error(message)
            return {"status": "error", "message": message}

        self._store_response(payload)
        cache.delete(LAST_ERROR_CACHE_KEY)
        return {
            "status": "ok",
            "subscription": payload.get("subscription"),
            "campaigns": payload.get("campaigns", []),
        }

    def status_snapshot(self) -> dict[str, Any]:
        state = AdminServiceState.get_solo()
        last_error = cache.get(LAST_ERROR_CACHE_KEY) or {}
        return {
            "configured": self.is_configured(),
            "heartbeat_enabled": settings.ADMIN_SERVICE_HEARTBEAT_ENABLED,
            "enforcement": enforcement_snapshot(),
            "last_synced_at": _iso_or_none(state.last_synced_at),
            "last_error_at": _iso_or_none(state.last_error_at) or last_error.get("at"),
            "last_error_message": state.last_error_message or last_error.get("message"),
            "subscription": state.subscription or get_cached_admin_subscription(),
            "campaigns": state.campaigns or [],
            "support_unread": state.support_unread,
        }

    def list_support_threads(self) -> list[dict[str, Any]]:
        payload = self._get("api/agent/support/threads")
        if not isinstance(payload, list):
            raise AdminAgentError("Некорректный ответ support API")
        return payload

    def create_support_thread(
        self,
        *,
        subject: str,
        priority: str,
        body: str,
        author_name: str | None,
    ) -> dict[str, Any]:
        payload = self._post(
            "api/agent/support/threads",
            {
                "subject": subject,
                "priority": priority,
                "author_name": author_name,
                "body": body,
            },
        )
        if not isinstance(payload, dict):
            raise AdminAgentError("Некорректный ответ support API")
        return payload

    def list_support_messages(self, thread_id: int) -> list[dict[str, Any]]:
        payload = self._get(f"api/agent/support/threads/{thread_id}/messages")
        if not isinstance(payload, list):
            raise AdminAgentError("Некорректный ответ support API")
        return payload

    def reply_support_thread(
        self,
        *,
        thread_id: int,
        body: str,
        author_name: str | None,
    ) -> dict[str, Any]:
        payload = self._post(
            f"api/agent/support/threads/{thread_id}/messages",
            {"author_name": author_name, "body": body},
        )
        if not isinstance(payload, dict):
            raise AdminAgentError("Некорректный ответ support API")
        return payload

    def _get(self, path: str) -> Any:
        self._ensure_configured()
        http = self.session or requests.Session()
        try:
            response = http.get(
                self.api_url(path),
                headers={"X-Agent-Token": settings.ADMIN_SERVICE_AGENT_TOKEN},
                timeout=settings.ADMIN_SERVICE_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise AdminAgentError(str(exc)) from exc
        return self._parse_response(response)

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        self._ensure_configured()
        http = self.session or requests.Session()
        try:
            response = http.post(
                self.api_url(path),
                json=payload,
                headers={"X-Agent-Token": settings.ADMIN_SERVICE_AGENT_TOKEN},
                timeout=settings.ADMIN_SERVICE_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise AdminAgentError(str(exc)) from exc
        return self._parse_response(response)

    def _ensure_configured(self) -> None:
        if not self.is_configured():
            raise AdminAgentError("RepireCRM Admin не настроен")

    def _parse_response(self, response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise AdminAgentError("RepireCRM Admin вернул не JSON") from exc
        status_code = getattr(response, "status_code", 200)
        if status_code >= 400:
            message = (
                _error_message(payload) or f"Ошибка RepireCRM Admin: HTTP {status_code}"
            )
            raise AdminAgentError(message)
        return payload

    def _store_response(self, payload: dict[str, Any]) -> None:
        synced_at = timezone.now()
        state = AdminServiceState.get_solo()
        state.subscription = payload.get("subscription") or {}
        state.campaigns = payload.get("campaigns") or []
        state.support_unread = int(payload.get("support_unread") or 0)
        state.server_time = _parse_server_time(payload.get("server_time"))
        state.raw_response = payload
        state.last_synced_at = synced_at
        state.last_error_message = ""
        state.save(
            update_fields=[
                "subscription",
                "campaigns",
                "support_unread",
                "server_time",
                "raw_response",
                "last_synced_at",
                "last_error_message",
                "updated_at",
            ]
        )
        cache.set(LAST_RESPONSE_CACHE_KEY, payload, CACHE_TTL_SECONDS)
        cache.set(LAST_SUBSCRIPTION_CACHE_KEY, state.subscription, CACHE_TTL_SECONDS)

    def _store_error(self, message: str) -> None:
        now = timezone.now()
        state = AdminServiceState.get_solo()
        state.last_error_at = now
        state.last_error_message = message[:2000]
        state.save(update_fields=["last_error_at", "last_error_message", "updated_at"])
        cache.set(
            LAST_ERROR_CACHE_KEY,
            {"message": message, "at": now.isoformat()},
            CACHE_TTL_SECONDS,
        )


def get_cached_admin_subscription() -> dict[str, Any] | None:
    return cache.get(LAST_SUBSCRIPTION_CACHE_KEY)


def _parse_server_time(value: str | None):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed and timezone.is_naive(parsed):
        return timezone.make_aware(parsed, datetime_timezone.utc)
    return parsed


def _iso_or_none(value) -> str | None:
    return value.isoformat() if value else None


def _error_message(payload: Any) -> str | None:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("code")
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return None
