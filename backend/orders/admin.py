from django.contrib import admin

from .models import (
    AdditionalService,
    Order,
    OrderAuditLog,
    OrderService,
    OrderStatusHistory,
    RepairService,
    RepairStage,
)


class OrderServiceInline(admin.TabularInline):
    model = OrderService
    extra = 0


class RepairStageInline(admin.TabularInline):
    model = RepairStage
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "shop",
        "status",
        "priority",
        "created_at",
    )
    list_filter = ("status", "priority", "shop")
    search_fields = (
        "order_number",
        "customer__phone",
        "customer__first_name",
        "customer__last_name",
    )
    inlines = (OrderServiceInline, RepairStageInline)


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "old_status", "new_status", "changed_by", "changed_at")
    list_filter = ("new_status", "changed_at")
    search_fields = ("order__order_number",)


@admin.register(OrderAuditLog)
class OrderAuditLogAdmin(admin.ModelAdmin):
    list_display = ("order", "action", "actor", "message", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("order__order_number", "message")
    readonly_fields = ("created_at",)


@admin.register(RepairStage)
class RepairStageAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "title",
        "customer_visible",
        "position",
        "created_by",
        "created_at",
    )
    list_filter = ("customer_visible", "created_at")
    search_fields = ("order__order_number", "title", "description")


admin.site.register(AdditionalService)
admin.site.register(RepairService)
