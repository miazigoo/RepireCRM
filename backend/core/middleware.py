import uuid

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from shops.models import Shop


class RequestIdMiddleware(MiddlewareMixin):
    """Attach a unique X-Request-Id to every request/response for tracing."""

    def process_request(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        request.request_id = request_id

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-Id"] = request_id
        return response


class ShopMiddleware(MiddlewareMixin):
    """Attach the current shop to authenticated API requests.

    Only runs for authenticated users and only on /api/ paths to avoid
    unnecessary DB queries for static files or the Django admin.
    """

    _API_PREFIX = "/api/"

    def process_request(self, request):
        # Skip non-API paths and unauthenticated users early
        if not request.path.startswith(self._API_PREFIX):
            return None
        if not request.user.is_authenticated:
            return None

        shop_id = request.META.get("HTTP_X_CURRENT_SHOP") or request.session.get(
            "current_shop_id"
        )

        if shop_id:
            try:
                shop = Shop.objects.get(id=int(shop_id), is_active=True)
                if request.user.can_access_shop(shop):
                    request.current_shop = shop
                    request.session["current_shop_id"] = shop.id
                    # Only persist if the shop actually changed
                    if request.user.current_shop_id != shop.id:
                        request.user.current_shop = shop
                        request.user.save(update_fields=["current_shop"])
                else:
                    return JsonResponse(
                        {"error": "Access denied to this shop"}, status=403
                    )
            except (Shop.DoesNotExist, ValueError):
                pass

        # Fall back to the first available shop if none resolved
        if not hasattr(request, "current_shop"):
            available_shops = request.user.get_available_shops()
            first = available_shops.first()
            if first:
                request.current_shop = first
                request.session["current_shop_id"] = first.id

        return None
