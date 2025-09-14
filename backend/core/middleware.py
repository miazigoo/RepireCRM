from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from shops.models import Shop
import json


class ShopMiddleware(MiddlewareMixin):
    """Middleware для обработки текущего магазина пользователя"""

    def process_request(self, request):
        if request.user.is_authenticated:
            # Получаем ID текущего магазина из заголовка или сессии
            shop_id = (
                    request.META.get('HTTP_X_CURRENT_SHOP') or
                    request.session.get('current_shop_id')
            )

            if shop_id:
                try:
                    shop = Shop.objects.get(id=shop_id, is_active=True)
                    if request.user.can_access_shop(shop):
                        request.current_shop = shop
                        request.session['current_shop_id'] = shop.id

                        # Обновляем current_shop пользователя
                        if request.user.current_shop != shop:
                            request.user.current_shop = shop
                            request.user.save(update_fields=['current_shop'])
                    else:
                        return JsonResponse(
                            {'error': 'Access denied to this shop'},
                            status=403
                        )
                except Shop.DoesNotExist:
                    pass

            # Если магазин не установлен, используем первый доступный
            if not hasattr(request, 'current_shop'):
                available_shops = request.user.get_available_shops()
                if available_shops.exists():
                    request.current_shop = available_shops.first()
                    request.session['current_shop_id'] = request.current_shop.id