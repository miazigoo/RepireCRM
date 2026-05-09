from django.contrib import admin

from .models import OrderDiscount, PromoCode, Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "discount_type",
        "value",
        "min_order_amount",
        "is_active",
        "auto_apply",
        "starts_at",
        "ends_at",
    )
    list_filter = ("is_active", "auto_apply", "discount_type")
    search_fields = ("name", "description")
    filter_horizontal = ("shops",)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "promotion",
        "is_active",
        "usage_limit",
        "starts_at",
        "ends_at",
    )
    list_filter = ("is_active", "promotion")
    search_fields = ("code", "promotion__name")


@admin.register(OrderDiscount)
class OrderDiscountAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "label",
        "source",
        "amount",
        "promotion",
        "promo_code",
        "created_at",
    )
    list_filter = ("source", "promotion")
    search_fields = ("order__order_number", "label", "promo_code__code")
