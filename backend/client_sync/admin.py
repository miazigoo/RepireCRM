from django.contrib import admin

from .models import ClientPortalIntegration, ClientSyncAction, ClientSyncOrderState


@admin.register(ClientPortalIntegration)
class ClientPortalIntegrationAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "enabled",
        "tenant_key",
        "base_url",
        "client_domain",
        "auth_policy",
        "last_push_at",
        "last_pull_at",
    )
    list_filter = ("enabled", "auth_policy")
    search_fields = ("organization__name", "tenant_key", "base_url", "client_domain")


@admin.register(ClientSyncOrderState)
class ClientSyncOrderStateAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "integration",
        "status",
        "remote_order_id",
        "attempts",
        "last_synced_at",
    )
    list_filter = ("status", "integration")
    search_fields = ("order__order_number", "remote_order_id", "last_error")


@admin.register(ClientSyncAction)
class ClientSyncActionAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "integration",
        "action_type",
        "status",
        "related_order",
        "related_task",
        "received_at",
        "applied_at",
        "synced_back_at",
    )
    list_filter = ("status", "action_type", "integration")
    search_fields = ("external_id", "related_order__order_number", "error_message")
