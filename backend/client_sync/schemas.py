from typing import Optional

from ninja import Schema


class ClientPortalIntegrationSchema(Schema):
    id: int
    organization_id: int
    organization_name: str
    enabled: bool
    configured: bool
    base_url: Optional[str] = None
    tenant_key: str
    client_domain: Optional[str] = None
    auth_policy: str
    support_phone: Optional[str] = None
    support_email: Optional[str] = None
    brand_name: Optional[str] = None
    accent_color: Optional[str] = None
    api_key_configured: bool
    last_push_at: Optional[str] = None
    last_pull_at: Optional[str] = None
    last_error: Optional[str] = None


class ClientPortalIntegrationUpdateSchema(Schema):
    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    tenant_key: Optional[str] = None
    client_domain: Optional[str] = None
    auth_policy: Optional[str] = None
    support_phone: Optional[str] = None
    support_email: Optional[str] = None
    brand_name: Optional[str] = None
    accent_color: Optional[str] = None


class ClientSyncRunSchema(Schema):
    push: bool = True
    pull: bool = True
    limit: int = 100


class ClientSyncStatusSchema(Schema):
    integration: ClientPortalIntegrationSchema
    order_states: dict
    actions: dict
