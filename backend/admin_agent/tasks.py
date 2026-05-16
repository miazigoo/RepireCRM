from celery import shared_task

from .services import AdminAgentService


@shared_task(name="admin_agent.tasks.send_admin_heartbeat")
def send_admin_heartbeat():
    return AdminAgentService().send_heartbeat()
