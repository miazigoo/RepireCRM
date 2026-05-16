from typing import Any

from ninja import Schema
from pydantic import Field


class AdminSupportThreadCreateSchema(Schema):
    subject: str = Field(min_length=2, max_length=255)
    priority: str = Field(default="normal", max_length=40)
    body: str = Field(min_length=1, max_length=10000)
    author_name: str | None = Field(default=None, max_length=255)


class AdminSupportMessageCreateSchema(Schema):
    body: str = Field(min_length=1, max_length=10000)
    author_name: str | None = Field(default=None, max_length=255)


class AdminAgentStatusSchema(Schema):
    configured: bool
    heartbeat_enabled: bool
    enforcement: dict[str, Any]
    last_synced_at: str | None = None
    last_error_at: str | None = None
    last_error_message: str | None = None
    subscription: dict[str, Any] | None = None
    campaigns: list[dict[str, Any]] = Field(default_factory=list)
    support_unread: int = 0
