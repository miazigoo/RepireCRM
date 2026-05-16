from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from admin_agent.enforcement import subscription_denial_reason
from admin_agent.services import AdminAgentService


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "server_time": "2026-05-16T12:00:00Z",
            "subscription": {"status": "active", "access_allowed": True},
            "campaigns": [{"title": "Demo"}],
            "support_unread": 2,
        }


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse()

    def get(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse()


@override_settings(
    ADMIN_SERVICE_HEARTBEAT_ENABLED=False,
    ADMIN_SERVICE_URL="https://admin.example.com",
    ADMIN_SERVICE_AGENT_TOKEN="token",
)
def test_admin_heartbeat_skips_when_disabled():
    assert AdminAgentService().send_heartbeat() == {
        "status": "skipped",
        "reason": "disabled",
    }


@override_settings(
    ADMIN_SERVICE_HEARTBEAT_ENABLED=True,
    ADMIN_SERVICE_URL="https://admin.example.com",
    ADMIN_SERVICE_AGENT_TOKEN="token",
    ADMIN_SERVICE_TIMEOUT_SECONDS=3,
    APP_VERSION="test-version",
)
def test_admin_heartbeat_posts_metrics():
    session = FakeSession()
    service = AdminAgentService(session=session)
    service.build_payload = lambda: {
        "version": "test-version",
        "metrics": {"revenue_month": 0, "orders_total": 0},
    }
    service._store_response = lambda payload: None

    result = service.send_heartbeat()

    assert result["status"] == "ok"
    assert (
        session.calls[0]["args"][0] == "https://admin.example.com/api/agent/heartbeat"
    )
    assert session.calls[0]["kwargs"]["headers"] == {"X-Agent-Token": "token"}
    assert session.calls[0]["kwargs"]["timeout"] == 3
    payload = session.calls[0]["kwargs"]["json"]
    assert payload["version"] == "test-version"
    assert payload["metrics"]["revenue_month"] == 0
    assert payload["metrics"]["orders_total"] == 0


@override_settings(
    ADMIN_SERVICE_HEARTBEAT_ENABLED=True,
    ADMIN_SERVICE_URL="https://admin.example.com",
    ADMIN_SERVICE_AGENT_TOKEN="token",
    ADMIN_SERVICE_TIMEOUT_SECONDS=3,
    APP_VERSION="test-version",
)
def test_admin_heartbeat_sends_response_to_persistence():
    stored = []
    service = AdminAgentService(session=FakeSession())
    service.build_payload = lambda: {
        "version": "test-version",
        "metrics": {"revenue_month": 0, "orders_total": 0},
    }
    service._store_response = stored.append

    result = service.send_heartbeat()

    assert result["status"] == "ok"
    assert stored[0]["subscription"]["status"] == "active"
    assert stored[0]["campaigns"][0]["title"] == "Demo"
    assert stored[0]["support_unread"] == 2


@override_settings(
    ADMIN_SERVICE_URL="https://admin.example.com",
    ADMIN_SERVICE_AGENT_TOKEN="token",
    ADMIN_SERVICE_TIMEOUT_SECONDS=3,
)
def test_admin_support_uses_agent_token_header():
    class SupportResponse:
        status_code = 200

        def json(self):
            return [{"id": 10, "subject": "Need help"}]

    class SupportSession:
        def __init__(self):
            self.calls = []

        def get(self, *args, **kwargs):
            self.calls.append({"args": args, "kwargs": kwargs})
            return SupportResponse()

    session = SupportSession()
    result = AdminAgentService(session=session).list_support_threads()

    assert result[0]["id"] == 10
    assert (
        session.calls[0]["args"][0]
        == "https://admin.example.com/api/agent/support/threads"
    )
    assert session.calls[0]["kwargs"]["headers"] == {"X-Agent-Token": "token"}


def test_revenue_metric_uses_kopecks():
    revenue = Decimal("123.45")
    assert int(revenue * 100) == 12345


@override_settings(ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS=72)
def test_subscription_enforcement_blocks_expired_access():
    reason = subscription_denial_reason(
        {
            "available": True,
            "last_synced_at": timezone.now(),
            "subscription": {
                "status": "expired",
                "access_allowed": False,
                "reason": "expired",
            },
        }
    )

    assert reason
    assert "ограничен" in reason


@override_settings(
    ADMIN_SERVICE_ENFORCEMENT_REQUIRE_SYNC=False,
    ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS=72,
)
def test_subscription_enforcement_allows_until_first_sync():
    assert subscription_denial_reason({"available": False}) is None


@override_settings(ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS=1)
def test_subscription_enforcement_blocks_stale_state():
    reason = subscription_denial_reason(
        {
            "available": True,
            "last_synced_at": timezone.now() - timedelta(hours=2),
            "subscription": {"status": "active", "access_allowed": True},
        }
    )

    assert reason
    assert "не подтверждалась" in reason
