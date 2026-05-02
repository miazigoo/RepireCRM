from django.contrib import admin

from .models import (
    Organization,
    OrganizationSubscription,
    Shop,
    ShopSettings,
    SubscriptionPlan,
)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "phone", "email")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "phone", "email")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "inn", "phone", "email")
    search_fields = ("name", "inn", "phone", "email")


@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    list_display = ("shop", "organization", "auto_order_numbering")
    list_select_related = ("shop", "organization")
    search_fields = ("shop__name", "organization__name")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "billing_period",
        "duration_days",
        "price",
        "is_active",
    )
    list_filter = ("billing_period", "is_active")
    search_fields = ("code", "name")


@admin.register(OrganizationSubscription)
class OrganizationSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "plan",
        "status",
        "started_at",
        "expires_at",
        "remaining_days",
        "color_bucket",
    )
    list_filter = ("status", "plan")
    list_select_related = ("organization", "plan")
    search_fields = ("organization__name", "plan__name")
    readonly_fields = ("remaining_days", "remaining_percent", "color_bucket")
