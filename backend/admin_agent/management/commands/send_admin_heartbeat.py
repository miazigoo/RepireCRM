from django.core.management.base import BaseCommand

from admin_agent.services import AdminAgentService


class Command(BaseCommand):
    help = "Send one RepireCRM Admin heartbeat now."

    def handle(self, *args, **options):
        result = AdminAgentService().send_heartbeat()
        self.stdout.write(self.style.SUCCESS(str(result)))
