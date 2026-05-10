from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import paginate

from users.statistics import resolve_period_range

from .models import Task, TaskComment, TaskTemplate
from .schemas import TaskCreateSchema, TaskSchema, TaskUpdateSchema
from .services import TaskService

router = Router(tags=["Задачи"])


def _current_task_shops(request):
    current_shop = getattr(request, "current_shop", None)
    if current_shop:
        return [current_shop]
    return request.auth.get_available_shops()


def _task_shop_scope_query(request):
    shops = _current_task_shops(request)
    return (
        Q(assignment_type=Task.AssignmentType.SHOP, assigned_shop__in=shops)
        | Q(assignment_type=Task.AssignmentType.ALL_SHOPS)
        | Q(assigned_to__shops__in=shops)
        | Q(assignment_type=Task.AssignmentType.ROLE, assigned_role=request.auth.role)
    )


def _can_manage_paid_tasks(user):
    return user.is_director or user.has_permission("users.manage_compensation")


def _can_assign_across_shops(user):
    return user.is_director or user.has_permission("tasks.view_all_tasks")


def _validate_task_assignment(
    request,
    assignment_type,
    assigned_to_id=None,
    assigned_shop_id=None,
):
    if assignment_type == Task.AssignmentType.ALL_SHOPS:
        if not request.auth.can_view_global_statistics():
            raise PermissionError(
                "Только директор может назначать задачи всем филиалам"
            )
        return

    if assignment_type == Task.AssignmentType.SHOP:
        if not assigned_shop_id:
            raise ValueError("Выберите филиал для задачи")
        from shops.models import Shop

        shop = get_object_or_404(Shop, id=assigned_shop_id, is_active=True)
        if not request.auth.can_access_shop(shop):
            raise PermissionError("Нет прав назначить задачу этому филиалу")
        return

    if assignment_type == Task.AssignmentType.INDIVIDUAL:
        if not assigned_to_id:
            raise ValueError("Выберите исполнителя задачи")
        User = get_user_model()
        assignee = get_object_or_404(User, id=assigned_to_id, is_active=True)
        if _can_assign_across_shops(request.auth):
            return
        available_shop_ids = request.auth.get_available_shops().values("id")
        if not assignee.shops.filter(id__in=available_shop_ids).exists():
            raise PermissionError("Нет прав назначить задачу этому сотруднику")


@router.get("/", response=list[TaskSchema])
@paginate
def list_tasks(
    request,
    status: str = None,
    priority: str = None,
    search: str = None,
    assigned_to_me: bool = False,
    created_by_me: bool = False,
    all_shops: bool = False,
):
    """Список задач"""
    if not request.auth.has_permission("tasks.view_task"):
        raise PermissionError("Нет прав для просмотра задач")

    queryset = Task.objects.select_related(
        "category", "assigned_to", "assigned_shop", "assigned_role", "created_by"
    ).prefetch_related("comments")

    if all_shops and not (
        request.auth.is_director or request.auth.has_permission("tasks.view_all_tasks")
    ):
        raise PermissionError("Нет прав смотреть задачи всех филиалов")

    if assigned_to_me:
        # Задачи, назначенные текущему пользователю
        user_tasks = Q(assigned_to=request.auth)

        # Задачи магазинов пользователя
        user_shops = _current_task_shops(request)
        shop_tasks = Q(assignment_type="shop", assigned_shop__in=user_shops)

        # Задачи для всех
        all_tasks = Q(assignment_type="all_shops")

        # Задачи по роли
        role_tasks = Q(assignment_type="role", assigned_role=request.auth.role)

        queryset = queryset.filter(user_tasks | shop_tasks | all_tasks | role_tasks)

    elif all_shops and (
        request.auth.is_director or request.auth.has_permission("tasks.view_all_tasks")
    ):
        pass

    elif not (
        request.auth.is_director or request.auth.has_permission("tasks.view_all_tasks")
    ):
        # Ограничиваем видимость для обычных пользователей
        available_shops = _current_task_shops(request)
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
    else:
        queryset = queryset.filter(_task_shop_scope_query(request)).distinct()

    if status:
        queryset = queryset.filter(status=status)

    if priority:
        queryset = queryset.filter(priority=priority)

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    if created_by_me:
        queryset = queryset.filter(created_by=request.auth)

    return queryset.order_by("-created_at")


@router.post("/", response={201: TaskSchema, 400: dict})
def create_task(request, data: TaskCreateSchema):
    """Создание новой задачи"""
    if not request.auth.has_permission("tasks.add_task"):
        raise PermissionError("Нет прав для создания задач")

    if data.is_paid and not _can_manage_paid_tasks(request.auth):
        raise PermissionError("Нет прав назначать оплачиваемые задачи")
    _validate_task_assignment(
        request,
        data.assignment_type,
        assigned_to_id=data.assigned_to_id,
        assigned_shop_id=data.assigned_shop_id,
    )

    try:
        with transaction.atomic():
            payload = data.model_dump()
            if not payload.get("payment_amount"):
                payload["payment_amount"] = Decimal("0")
            payload["attachments"] = payload.get("attachments") or []
            payload["recurrence_pattern"] = payload.get("recurrence_pattern") or {}
            task = Task.objects.create(**payload, created_by=request.auth)

            # Отправляем уведомления исполнителям
            service = TaskService()
            service.notify_assignees(task)

            return 201, task

    except Exception as e:
        return 400, {"error": str(e)}


@router.get("/my-tasks-summary", response=dict)
def get_my_tasks_summary(request):
    """Сводка по задачам пользователя"""
    if not request.auth.has_permission("tasks.view_task"):
        raise PermissionError("Нет прав для просмотра задач")

    # Задачи, назначенные пользователю
    user_tasks = Q(assigned_to=request.auth)
    user_shops = _current_task_shops(request)
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
        "completed_this_month": my_tasks.filter(
            status=Task.Status.COMPLETED,
            completed_at__date__gte=today.replace(day=1),
        ).count(),
        "paid_tasks_amount": float(
            my_tasks.filter(
                status=Task.Status.COMPLETED,
                is_paid=True,
                completed_at__date__gte=today.replace(day=1),
            ).aggregate(total=Sum("payment_amount"))["total"]
            or 0
        ),
        "priority_breakdown": dict(
            my_tasks.values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        ),
    }


@router.get("/statistics", response=dict)
def get_tasks_statistics(
    request,
    period: str = "month",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    employee_id: int | None = None,
    all_shops: bool = False,
):
    """Статистика по задачам за период."""
    if not request.auth.has_permission("tasks.view_task"):
        raise PermissionError("Нет прав для просмотра задач")

    start_date, end_date = resolve_period_range(period, date_from, date_to)
    queryset = Task.objects.all()

    if all_shops and not (
        request.auth.is_director or request.auth.has_permission("tasks.view_all_tasks")
    ):
        raise PermissionError("Нет прав смотреть задачи всех филиалов")

    if employee_id:
        if not (
            request.auth.id == employee_id
            or request.auth.is_director
            or request.auth.has_permission("tasks.view_all_tasks")
        ):
            raise PermissionError("Нет прав смотреть задачи другого сотрудника")
        queryset = queryset.filter(
            Q(assigned_to_id=employee_id) | Q(completed_by_id=employee_id)
        )
        if not all_shops:
            queryset = queryset.filter(_task_shop_scope_query(request)).distinct()
    elif all_shops:
        pass
    elif not (
        request.auth.is_director or request.auth.has_permission("tasks.view_all_tasks")
    ):
        user_shops = _current_task_shops(request)
        queryset = queryset.filter(
            Q(created_by=request.auth)
            | Q(assigned_to=request.auth)
            | Q(assignment_type="shop", assigned_shop__in=user_shops)
            | Q(assignment_type="all_shops")
            | Q(assignment_type="role", assigned_role=request.auth.role)
        )
    else:
        queryset = queryset.filter(_task_shop_scope_query(request)).distinct()

    period_tasks = queryset.filter(created_at__range=[start_date, end_date])
    completed_tasks = queryset.filter(
        status=Task.Status.COMPLETED,
        completed_at__range=[start_date, end_date],
    )

    return {
        "period": {
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
        },
        "total": period_tasks.count(),
        "completed": completed_tasks.count(),
        "paid_amount": float(
            completed_tasks.filter(is_paid=True).aggregate(total=Sum("payment_amount"))[
                "total"
            ]
            or 0
        ),
        "by_status": list(
            period_tasks.values("status").annotate(count=Count("id")).order_by("status")
        ),
        "by_kind": list(
            period_tasks.values("kind").annotate(count=Count("id")).order_by("kind")
        ),
    }


@router.get("/templates", response=list[dict])
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


@router.put("/{task_id}", response=dict)
def update_task(request, task_id: int, data: TaskUpdateSchema):
    """Обновление задачи"""
    task = get_object_or_404(Task, id=task_id)
    incoming = data.model_dump(exclude_unset=True)
    if incoming.get("attachments") is None:
        incoming.pop("attachments", None)
    if incoming.get("recurrence_pattern") is None:
        incoming.pop("recurrence_pattern", None)

    # Проверяем права на редактирование
    if not request.auth.has_permission("tasks.change_task"):
        # Исполнители могут обновлять только статус и прогресс
        if request.auth not in task.get_assignees():
            raise PermissionError("Нет прав для редактирования задачи")

        # Ограничиваем поля для исполнителей
        allowed_fields = {"status", "substatus", "progress_percent", "actual_hours"}
        update_fields = set(incoming.keys())
        if not update_fields.issubset(allowed_fields):
            raise PermissionError(
                "Исполнители могут обновлять только статус и прогресс"
            )
    elif {"is_paid", "payment_amount"} & set(incoming.keys()):
        if not _can_manage_paid_tasks(request.auth):
            raise PermissionError("Нет прав менять оплату задачи")

    assignment_fields = {"assignment_type", "assigned_to_id", "assigned_shop_id"}
    if assignment_fields & set(incoming.keys()):
        _validate_task_assignment(
            request,
            incoming.get("assignment_type", task.assignment_type),
            assigned_to_id=incoming.get("assigned_to_id", task.assigned_to_id),
            assigned_shop_id=incoming.get("assigned_shop_id", task.assigned_shop_id),
        )

    try:
        # Сохраняем старый статус для уведомлений
        old_status = task.status

        # Обновляем поля
        for field, value in incoming.items():
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
def add_task_comment(request, task_id: int, text: str, attachments: list[dict] = None):
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
