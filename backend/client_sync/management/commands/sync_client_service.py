from client_sync.management.commands.sync_client_portal import (
    Command as SyncClientPortalCommand,
)


class Command(SyncClientPortalCommand):
    help = "Синхронизировать CRM с внешним клиентским сервисом."
