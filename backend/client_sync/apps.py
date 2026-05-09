from django.apps import AppConfig


class ClientSyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "client_sync"
    verbose_name = "Синхронизация клиентского кабинета"
