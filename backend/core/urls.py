from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .api_app import api

# Подключаем роутеры
from API.auth.router import router as auth_router
from API.customers.router import router as customers_router
from API.orders.router import router as orders_router

api.add_router("/auth", auth_router)
api.add_router("/customers", customers_router)
api.add_router("/orders", orders_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)