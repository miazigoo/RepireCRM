from ninja import Schema


class ClientPortalIntegrationSchema(Schema):
    id: int
    organization_id: int
    organization_name: str
    enabled: bool
    configured: bool
    base_url: str | None = None
    tenant_key: str
    client_domain: str | None = None
    auth_policy: str
    support_phone: str | None = None
    support_email: str | None = None
    brand_name: str | None = None
    accent_color: str | None = None
    portal_banner_enabled: bool = False
    portal_banner_title: str | None = None
    portal_banner_subtitle: str | None = None
    portal_banner_image_url: str | None = None
    portal_banner_link_url: str | None = None
    api_key_configured: bool
    last_push_at: str | None = None
    last_pull_at: str | None = None
    last_error: str | None = None


class ClientPortalIntegrationUpdateSchema(Schema):
    enabled: bool | None = None
    base_url: str | None = None
    api_key: str | None = None
    tenant_key: str | None = None
    client_domain: str | None = None
    auth_policy: str | None = None
    support_phone: str | None = None
    support_email: str | None = None
    brand_name: str | None = None
    accent_color: str | None = None
    portal_banner_enabled: bool | None = None
    portal_banner_title: str | None = None
    portal_banner_subtitle: str | None = None
    portal_banner_image_url: str | None = None
    portal_banner_link_url: str | None = None


class ClientSyncRunSchema(Schema):
    push: bool = True
    pull: bool = True
    limit: int = 100


class ClientSyncStatusSchema(Schema):
    integration: ClientPortalIntegrationSchema
    order_states: dict
    actions: dict
