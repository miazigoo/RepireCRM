from celery import shared_task

from .services import TaskService


@shared_task(name="tasks.tasks.low_stock_scan")
def low_stock_scan():
    service = TaskService()
    created = service.create_low_stock_tasks()
    return {"created": created}
