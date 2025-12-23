from typing import List, Optional

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router
from ninja.pagination import paginate

from .models import Task, TaskCategory, TaskComment, TaskTemplate
from .schemas import TaskCreateSchema, TaskSchema, TaskUpdateSchema
from .services import TaskService

router = Router(tags=["Задачи"])


@router.get("/", response=List[TaskSchema])
@paginate
def list_tasks(request, status: str = None, assigned_to_me: bool = False):
    """Список задач"""
    if not request.auth.has_permission("tasks.view_task"):
        raise PermissionError("Нет прав для просмотра задач")

    queryset = Task.objects.select_related(
        "category", "assigned_to", "assigned_shop", "assigned_role", "created_by"
    ).prefetch_related("comments")

    if assigned_to_me:
        # Задачи, назначенные текущему пользователю
        user_tasks = Q(assigned_to=request.auth)

        # Задачи магазинов пользователя
        user_shops = request.auth.get_available_shops()
        shop_tasks = Q(assignment_type="shop", assigned_shop__in=user_shops)

        # Задачи для всех
        all_tasks = Q(assignment_type="all_shops")

        # Задачи по роли
        role_tasks = Q(assignment_type="role", assigned_role=request.auth.role)

        queryset = queryset.filter(user_tasks | shop_tasks | all_tasks | role_tasks)

    elif not request.auth.is_director:
        # Ограничиваем видимость для обычных пользователей
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(
            Q(created_by=request.auth)
            | Q(assigned_to=request.auth)  # Созданные пользователем
            | Q(  # Назначенные пользователю
                assignment_type="shop", assigned_shop__in=available_shops
            )
            | Q(assignment_type="all_shops")  # Задачи магазинов
            | Q(  # Общие задачи
                assignment_type="role", assigned_role=request.auth.role
            )  # Задачи роли
        )

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


@router.post("/", response=dict)
def create_task(request, data: TaskCreateSchema):
    """Создание новой задачи"""
    if not request.auth.has_permission("tasks.add_task"):
        raise PermissionError("Нет прав для создания задач")

    # Проверяем права на назначение задач
    if data.assignment_type == "all_shops" and not request.auth.is_director:
        raise PermissionError("Только директор может назначать задачи всем магазинам")

    try:
        with transaction.atomic():
            task = Task.objects.create(**data.dict(), created_by=request.auth)

            # Отправляем уведомления исполнителям
            service = TaskService()
            service.notify_assignees(task)

            return {"success": True, "task_id": task.id, "title": task.title}

    except Exception as e:
        return {"error": str(e)}


@router.put("/{task_id}", response=dict)
def update_task(request, task_id: int, data: TaskUpdateSchema):
    """Обновление задачи"""
    task = get_object_or_404(Task, id=task_id)

    # Проверяем права на редактирование
    if not request.auth.has_permission("tasks.change_task"):
        # Исполнители могут обновлять только статус и прогресс
        if request.auth not in task.get_assignees():
            raise PermissionError("Нет прав для редактирования задачи")

        # Ограничиваем поля для исполнителей
        allowed_fields = {"status", "progress_percent", "actual_hours"}
        update_fields = set(data.dict(exclude_unset=True).keys())
        if not update_fields.issubset(allowed_fields):
            raise PermissionError(
                "Исполнители могут обновлять только статус и прогресс"
            )

    try:
        # Сохраняем старый статус для уведомлений
        old_status = task.status

        # Обновляем поля
        for field, value in data.dict(exclude_unset=True).items():
            setattr(task, field, value)

        # Устанавливаем исполнителя при завершении
        if task.status == Task.Status.COMPLETED and not task.completed_by:
            task.completed_by = request.auth

        task.save()

        # Отправляем уведомления при изменении статуса
        if task.status != old_status:
            service = TaskService()
            service.notify_status_change(task, old_status)

        return {"success": True, "task_id": task.id, "status": task.status}

    except Exception as e:
        return {"error": str(e)}


@router.post("/{task_id}/comments", response=dict)
def add_task_comment(request, task_id: int, text: str, attachments: List[dict] = None):
    """Добавление комментария к задаче"""
    task = get_object_or_404(Task, id=task_id)

    # Проверяем доступ к задаче
    if not request.auth.has_permission("tasks.view_task"):
        if request.auth not in task.get_assignees() and task.created_by != request.auth:
            raise PermissionError("Нет доступа к задаче")

    comment = TaskComment.objects.create(
        task=task, author=request.auth, text=text, attachments=attachments or []
    )

    # Уведомляем участников задачи
    service = TaskService()
    service.notify_new_comment(task, comment)

    return {"success": True, "comment_id": comment.id}


@router.get("/my-tasks-summary", response=dict)
def get_my_tasks_summary(request):
    """Сводка по задачам пользователя"""
    if not request.auth.has_permission("tasks.view_task"):
        raise PermissionError("Нет прав для просмотра задач")

    # Задачи, назначенные пользователю
    user_tasks = Q(assigned_to=request.auth)
    user_shops = request.auth.get_available_shops()
    shop_tasks = Q(assignment_type="shop", assigned_shop__in=user_shops)
    all_tasks = Q(assignment_type="all_shops")
    role_tasks = Q(assignment_type="role", assigned_role=request.auth.role)

    my_tasks = Task.objects.filter(user_tasks | shop_tasks | all_tasks | role_tasks)

    # Статистика по статусам
    status_stats = my_tasks.values("status").annotate(count=Count("id"))

    # Просроченные задачи
    overdue_tasks = my_tasks.filter(
        due_date__lt=timezone.now(),
        status__in=[Task.Status.PENDING, Task.Status.IN_PROGRESS],
    ).count()

    # Задачи на сегодня
    today = timezone.now().date()
    today_tasks = my_tasks.filter(
        due_date__date=today, status__in=[Task.Status.PENDING, Task.Status.IN_PROGRESS]
    ).count()

    return {
        "total_tasks": my_tasks.count(),
        "status_breakdown": {item["status"]: item["count"] for item in status_stats},
        "overdue_tasks": overdue_tasks,
        "due_today": today_tasks,
        "priority_breakdown": dict(
            my_tasks.values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        ),
    }


@router.get("/templates", response=List[dict])
def list_task_templates(request):
    """Список шаблонов задач"""
    if not request.auth.has_permission("tasks.view_template"):
        raise PermissionError("Нет прав для просмотра шаблонов")

    templates = TaskTemplate.objects.filter(is_active=True).select_related("category")

    return [
        {
            "id": template.id,
            "name": template.name,
            "category": template.category.name if template.category else None,
            "title_template": template.title_template,
            "default_priority": template.default_priority,
            "estimated_hours": float(template.estimated_hours)
            if template.estimated_hours
            else None,
        }
        for template in templates
    ]


@router.post("/create-from-template/{template_id}", response=dict)
def create_task_from_template(
    request, template_id: int, context: dict = None, **kwargs
):
    """Создание задачи из шаблона"""
    if not request.auth.has_permission("tasks.add_task"):
        raise PermissionError("Нет прав для создания задач")

    template = get_object_or_404(TaskTemplate, id=template_id)

    try:
        task = template.create_task(
            context=context or {}, created_by=request.auth, **kwargs
        )

        return {"success": True, "task_id": task.id, "title": task.title}

    except Exception as e:
        return {"error": str(e)}
