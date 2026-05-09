from typing import List

from django.db import models, transaction
from django.db.models import Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import File, Form, Query, Router
from ninja.files import UploadedFile
from ninja.pagination import PageNumberPagination, paginate

from customers.models import Customer
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from device.popular_models import (
    ensure_popular_device_models,
    popular_device_model_ordering,
)
from promotions.models import OrderDiscount
from Schemas.common import ErrorSchema
from users.models import User

from .models import (
    AdditionalService,
    Order,
    OrderApproval,
    OrderAuditLog,
    OrderService,
    OrderStatusHistory,
    RepairService,
    RepairStage,
)
from .orders_schemas import (
    AdditionalServiceCreateSchema,
    AdditionalServiceSchema,
    AdditionalServiceUpdateSchema,
    DeviceModelCreateSchema,
    DeviceModelSchema,
    OrderApprovalCreateSchema,
    OrderApprovalSchema,
    OrderAuditLogSchema,
    OrderCreateSchema,
    OrderFilterSchema,
    OrderSchema,
    OrderStatusHistorySchema,
    OrderUpdateSchema,
    RepairStageSchema,
    RepairStageUpdateSchema,
    WarrantyCaseCreateSchema,
    WarrantyOrderSummarySchema,
)
from .schemas_repair_services import RepairServiceSchema

router = Router(tags=["Заказы"])


class OrderPagination(PageNumberPagination):
    page_size = 20


def _get_accessible_order(request, order_id: int) -> Order:
    order = get_object_or_404(
        Order.objects.select_related(
            "shop",
            "customer",
            "device__model__brand",
            "device__model__device_type",
            "warranty_parent",
        ),
        id=order_id,
    )
    if not request.auth.can_access_shop(order.shop):
        raise PermissionError("Нет доступа к данному заказу")
    current_shop = getattr(request, "current_shop", None)
    if current_shop and order.shop_id != current_shop.id:
        raise PermissionError("Переключите филиал, чтобы открыть этот заказ")
    return order


def _log_order_audit(
    order: Order,
    action: str,
    message: str,
    actor=None,
    changes: dict | None = None,
) -> None:
    OrderAuditLog.objects.create(
        order=order,
        action=action,
        actor=actor,
        message=message,
        changes=changes or {},
    )


def _record_status_history(
    order: Order,
    old_status: str,
    new_status: str,
    user=None,
    comment: str = "",
) -> None:
    OrderStatusHistory.objects.create(
        order=order,
        old_status=old_status,
        new_status=new_status,
        changed_by=user,
        comment=comment,
    )
    _log_order_audit(
        order=order,
        action=OrderAuditLog.ActionChoices.STATUS_CHANGED,
        actor=user,
        message=f"Статус изменен на {order.get_status_display()}",
        changes={"old_status": old_status, "new_status": new_status},
    )


def _get_available_additional_service(request, service_id: int) -> AdditionalService:
    queryset = AdditionalService.objects.filter(id=service_id, is_active=True)
    current_shop = getattr(request, "current_shop", None)
    if current_shop:
        queryset = queryset.filter(Q(shops__isnull=True) | Q(shops=current_shop))
    service = queryset.distinct().first()
    if not service:
        raise Http404("Услуга недоступна в выбранном филиале")
    return service


def _with_order_relations(queryset):
    return queryset.select_related(
        "customer",
        "device__model__brand",
        "device__model__device_type",
        "shop",
        "created_by",
        "assigned_to",
        "warranty_parent",
    ).prefetch_related(
        Prefetch(
            "orderservice_set", queryset=OrderService.objects.select_related("service")
        ),
        Prefetch(
            "discounts",
            queryset=OrderDiscount.objects.select_related("promotion", "promo_code"),
        ),
    )


@router.get("/", response=List[OrderSchema])
@paginate(OrderPagination)
def list_orders(request, filters: OrderFilterSchema = Query(...)):
    """Получение списка заказов"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    # Базовый queryset с оптимизацией запросов
    queryset = _with_order_relations(Order.objects.all())

    # Выбранный филиал всегда ограничивает рабочий список заказов.
    if hasattr(request, "current_shop") and request.current_shop:
        queryset = queryset.filter(shop=request.current_shop)
    elif not request.auth.has_permission("orders.view_all_shops"):
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(shop__in=available_shops)

    # Применяем фильтры
    if filters.search:
        queryset = queryset.filter(
            Q(order_number__icontains=filters.search)
            | Q(customer__first_name__icontains=filters.search)
            | Q(customer__last_name__icontains=filters.search)
            | Q(customer__phone__icontains=filters.search)
            | Q(device__model__brand__name__icontains=filters.search)
            | Q(device__model__name__icontains=filters.search)
        )

    if filters.status:
        queryset = queryset.filter(status=filters.status)

    if filters.priority:
        queryset = queryset.filter(priority=filters.priority)

    if filters.customer_id:
        queryset = queryset.filter(customer_id=filters.customer_id)

    if filters.assigned_to_id:
        queryset = queryset.filter(assigned_to_id=filters.assigned_to_id)

    if filters.created_from:
        queryset = queryset.filter(created_at__gte=filters.created_from)

    if filters.created_to:
        queryset = queryset.filter(created_at__lte=filters.created_to)

    if filters.estimated_completion_from:
        queryset = queryset.filter(
            estimated_completion__gte=filters.estimated_completion_from
        )

    if filters.estimated_completion_to:
        queryset = queryset.filter(
            estimated_completion__lte=filters.estimated_completion_to
        )

    return queryset.order_by("-created_at")


@router.get("/additional-services", response=List[AdditionalServiceSchema])
def list_additional_services(request, include_inactive: bool = False):
    """Получение списка дополнительных услуг"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра услуг")

    if include_inactive:
        if not request.auth.has_permission("orders.change_order"):
            raise PermissionError("Нет прав для управления услугами")
        queryset = AdditionalService.objects.all()
    else:
        queryset = AdditionalService.objects.filter(is_active=True)

    # Фильтруем по доступным в текущем магазине
    if hasattr(request, "current_shop") and request.current_shop:
        queryset = queryset.filter(
            Q(shops__isnull=True) | Q(shops=request.current_shop)
        ).distinct()

    return queryset.order_by("category", "name")


def _sync_service_shops(request, service: AdditionalService, shop_ids: list[int]):
    if not shop_ids:
        service.shops.clear()
        return
    shops = request.auth.get_available_shops().filter(id__in=shop_ids)
    if shops.count() != len(set(shop_ids)):
        raise PermissionError("Нет прав назначить услугу одному из филиалов")
    service.shops.set(shops)


@router.post(
    "/additional-services", response={201: AdditionalServiceSchema, 400: ErrorSchema}
)
def create_additional_service(request, data: AdditionalServiceCreateSchema):
    """Создание фиксированной услуги для заказов."""
    if not request.auth.has_permission("orders.change_order"):
        raise PermissionError("Нет прав для управления услугами")

    service = AdditionalService.objects.create(
        name=data.name.strip(),
        category=data.category,
        description=data.description or "",
        price=data.price,
        is_active=data.is_active,
    )
    _sync_service_shops(request, service, data.shop_ids)
    return 201, service


@router.put(
    "/additional-services/{service_id}",
    response={200: AdditionalServiceSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def update_additional_service(
    request, service_id: int, data: AdditionalServiceUpdateSchema
):
    """Редактирование услуги."""
    if not request.auth.has_permission("orders.change_order"):
        raise PermissionError("Нет прав для управления услугами")

    service = get_object_or_404(AdditionalService, id=service_id)
    incoming = data.dict(exclude_unset=True)
    shop_ids = incoming.pop("shop_ids", None)
    for field, value in incoming.items():
        if value is not None:
            setattr(service, field, value)
    service.save()
    if shop_ids is not None:
        _sync_service_shops(request, service, shop_ids)
    return service


@router.delete("/additional-services/{service_id}", response=dict)
def delete_additional_service(request, service_id: int):
    """Отключение услуги, чтобы она не предлагалась в новых заказах."""
    if not request.auth.has_permission("orders.change_order"):
        raise PermissionError("Нет прав для управления услугами")

    service = get_object_or_404(AdditionalService, id=service_id)
    service.is_active = False
    service.save(update_fields=["is_active", "updated_at"])
    return {"success": True}


@router.get("/statistics", response=dict)
def get_orders_statistics(request, all_shops: bool = False):
    """Получение статистики по заказам"""
    if not request.auth.has_permission("reports.view_analytics"):
        raise PermissionError("Нет прав для просмотра аналитики")

    from datetime import timedelta

    from django.db.models import Count
    from django.utils import timezone

    # Базовый queryset с учетом прав доступа
    queryset = Order.objects.all()
    if all_shops:
        if not request.auth.can_view_global_statistics():
            raise PermissionError("Нет прав для общей статистики по филиалам")
    elif hasattr(request, "current_shop") and request.current_shop:
        queryset = queryset.filter(shop=request.current_shop)
    elif not request.auth.has_permission("orders.view_all_shops"):
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(shop__in=available_shops)

    # Статистика за последние 30 дней
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_orders = queryset.filter(created_at__gte=thirty_days_ago)

    completed_orders = list(
        queryset.filter(status=Order.StatusChoices.COMPLETED).prefetch_related(
            "orderservice_set", "discounts"
        )
    )
    total_revenue = sum((order.total_cost for order in completed_orders), 0)
    recent_completed_orders = [
        order for order in completed_orders if order.created_at >= thirty_days_ago
    ]
    recent_revenue = sum((order.total_cost for order in recent_completed_orders), 0)

    # Статистика по статусам
    status_stats = (
        queryset.values("status").annotate(count=Count("id")).order_by("-count")
    )

    return {
        "total_orders": queryset.count(),
        "total_revenue": float(total_revenue or 0),
        "avg_order_value": float(
            total_revenue / len(completed_orders) if completed_orders else 0
        ),
        "recent_orders": recent_orders.count(),
        "recent_revenue": float(recent_revenue or 0),
        "status_distribution": list(status_stats),
        "period": "30 days",
    }


@router.get("/repair-services/suggest", response=List[RepairServiceSchema])
def suggest_repair_services(request, device_model_id: int):
    """Подсказки типовых работ под конкретную модель"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав")

    from device.models import DeviceModel

    dm = get_object_or_404(
        DeviceModel.objects.select_related("brand", "device_type"), id=device_model_id
    )

    qs = RepairService.objects.filter(is_active=True).filter(
        models.Q(model=dm)
        | models.Q(brand=dm.brand, model__isnull=True)
        | models.Q(device_type=dm.device_type, brand__isnull=True, model__isnull=True)
    )

    if hasattr(request, "current_shop") and request.current_shop:
        qs = qs.filter(
            models.Q(shops__isnull=True) | models.Q(shops=request.current_shop)
        ).distinct()

    return qs.order_by("name")


@router.get("/repair-services", response=List[RepairServiceSchema])
def list_repair_services(
    request,
    device_type_id: int = None,
    brand_id: int = None,
    model_id: int = None,
    search: str = None,
):
    """Список типовых работ с фильтрами"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав")

    qs = RepairService.objects.filter(is_active=True)

    # доступность в магазине
    if hasattr(request, "current_shop") and request.current_shop:
        qs = qs.filter(
            models.Q(shops__isnull=True) | models.Q(shops=request.current_shop)
        ).distinct()

    if model_id:
        qs = qs.filter(models.Q(model_id=model_id) | models.Q(model__isnull=True))
    if brand_id:
        qs = qs.filter(models.Q(brand_id=brand_id) | models.Q(brand__isnull=True))
    if device_type_id:
        qs = qs.filter(
            models.Q(device_type_id=device_type_id) | models.Q(device_type__isnull=True)
        )
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))

    return qs.order_by("brand__name", "model__name", "name")


@router.get("/device-models", response=List[DeviceModelSchema])
def list_device_models(request, search: str = None):
    """Список моделей устройств для формы заказа."""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра моделей устройств")

    ensure_popular_device_models()
    qs = DeviceModel.objects.select_related("brand", "device_type").filter(
        is_active=True
    )
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(model_number__icontains=search)
            | Q(brand__name__icontains=search)
            | Q(device_type__name__icontains=search)
        )

    return qs.annotate(popularity_rank=popular_device_model_ordering()).order_by(
        "popularity_rank", "brand__name", "name"
    )


@router.post("/device-models", response={201: DeviceModelSchema, 400: ErrorSchema})
def create_device_model(request, data: DeviceModelCreateSchema):
    """Создать модель устройства из формы заказа, если ее нет в справочнике."""
    if not request.auth.has_permission("orders.add_order"):
        raise PermissionError("Нет прав для создания моделей устройств")

    brand_name = data.brand_name.strip()
    model_name = data.name.strip()
    device_type_name = (data.device_type_name or "Смартфон").strip() or "Смартфон"
    if not brand_name or not model_name:
        return 400, {"error": "Укажите бренд и модель устройства"}

    brand, _ = DeviceBrand.objects.get_or_create(name=brand_name)
    device_type, _ = DeviceType.objects.get_or_create(
        name=device_type_name,
        defaults={"icon": "smartphone"},
    )
    model, _ = DeviceModel.objects.get_or_create(
        brand=brand,
        device_type=device_type,
        name=model_name,
        defaults={
            "model_number": data.model_number or "",
            "release_year": data.release_year,
        },
    )
    return 201, model


@router.get("/{order_id}/warranty-cases", response=List[WarrantyOrderSummarySchema])
def list_warranty_cases(request, order_id: int):
    """Гарантийные обращения, созданные по исходному заказу."""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    order = _get_accessible_order(request, order_id)
    return _with_order_relations(order.warranty_cases.all()).order_by("-created_at")


@router.post(
    "/{order_id}/warranty-cases",
    response={201: OrderSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def create_warranty_case(request, order_id: int, data: WarrantyCaseCreateSchema):
    """Создать бесплатный гарантийный заказ по выданному заказу."""
    if not request.auth.has_permission("orders.add_order"):
        raise PermissionError("Нет прав для создания заказов")

    source_order = _get_accessible_order(request, order_id)
    if source_order.is_warranty_case:
        return 400, {
            "error": "Гарантийный заказ не может быть исходным для новой гарантии"
        }
    if source_order.status != Order.StatusChoices.COMPLETED:
        return 400, {
            "error": "Гарантийный случай можно создать только по выданному заказу"
        }
    if not source_order.warranty_active:
        return 400, {"error": "Гарантия по этому заказу уже не действует"}

    reason = data.reason.strip()
    if not reason:
        return 400, {"error": "Укажите причину гарантийного обращения"}

    priority = data.priority or Order.PriorityChoices.HIGH
    if priority not in Order.PriorityChoices.values:
        return 400, {"error": "Некорректный приоритет гарантийного заказа"}

    problem_description = (
        data.problem_description.strip()
        if data.problem_description
        else f"Гарантийное обращение: {reason}"
    )

    try:
        with transaction.atomic():
            warranty_order = Order.objects.create(
                shop=source_order.shop,
                customer=source_order.customer,
                device=source_order.device,
                status=Order.StatusChoices.RECEIVED,
                priority=priority,
                problem_description=problem_description,
                accessories=source_order.accessories,
                device_condition=source_order.device_condition,
                cost_estimate=0,
                prepayment=0,
                created_by=request.auth,
                assigned_to=source_order.assigned_to,
                estimated_completion=data.estimated_completion,
                notes=f"Гарантийный случай по заказу {source_order.order_number}",
                is_warranty_case=True,
                warranty_parent=source_order,
                warranty_reason=reason,
                warranty_days=source_order.warranty_days,
            )
            _record_status_history(
                order=warranty_order,
                old_status="",
                new_status=warranty_order.status,
                user=request.auth,
                comment="Создан гарантийный заказ",
            )
            _log_order_audit(
                order=source_order,
                action=OrderAuditLog.ActionChoices.UPDATED,
                actor=request.auth,
                message=f"Создан гарантийный заказ {warranty_order.order_number}",
                changes={"warranty_order_id": warranty_order.id},
            )

            return 201, _with_order_relations(Order.objects.all()).get(
                id=warranty_order.id
            )
    except Http404:
        return 404, {"error": "Исходный заказ не найден"}
    except Exception as e:
        return 400, {"error": str(e)}


@router.get("/{order_id}", response=OrderSchema)
def get_order(request, order_id: int):
    """Получение заказа по ID"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    queryset = _with_order_relations(Order.objects.all())

    order = get_object_or_404(queryset, id=order_id)

    # Проверяем доступ к магазину заказа
    if not request.auth.can_access_shop(order.shop):
        raise PermissionError("Нет доступа к данному заказу")
    current_shop = getattr(request, "current_shop", None)
    if current_shop and order.shop_id != current_shop.id:
        raise PermissionError("Переключите филиал, чтобы открыть этот заказ")

    return order


@router.post("/", response={201: OrderSchema, 400: ErrorSchema})
def create_order(request, data: OrderCreateSchema):
    """Создание нового заказа"""
    if not request.auth.has_permission("orders.add_order"):
        raise PermissionError("Нет прав для создания заказов")

    if not hasattr(request, "current_shop") or not request.current_shop:
        return 400, {"error": "Не выбран текущий магазин"}

    try:
        with transaction.atomic():
            # Получаем или создаем клиента
            customer = get_object_or_404(Customer, id=data.customer_id)

            # Создаем или получаем устройство
            device_model = get_object_or_404(DeviceModel, id=data.device.model_id)
            device = Device.objects.create(
                model=device_model,
                **data.device.dict(exclude={"model_id"}, exclude_none=True),
            )

            # Создаем заказ
            order = Order.objects.create(
                shop=request.current_shop,
                customer=customer,
                device=device,
                problem_description=data.problem_description,
                accessories=data.accessories or "",
                device_condition=data.device_condition or "",
                cost_estimate=data.cost_estimate,
                priority=data.priority,
                estimated_completion=data.estimated_completion,
                created_by=request.auth,
            )
            _record_status_history(
                order=order,
                old_status="",
                new_status=order.status,
                user=request.auth,
                comment="Заказ создан",
            )
            _log_order_audit(
                order=order,
                action=OrderAuditLog.ActionChoices.CREATED,
                actor=request.auth,
                message="Заказ создан сотрудником",
            )

            # Добавляем дополнительные услуги
            if data.additional_services:
                for service_data in data.additional_services:
                    quantity = int(service_data.get("quantity", 1))
                    if quantity < 1:
                        return 400, {"error": "Количество услуги должно быть больше 0"}
                    service = _get_available_additional_service(
                        request, service_data["service_id"]
                    )
                    OrderService.objects.create(
                        order=order,
                        service=service,
                        quantity=quantity,
                        price=service.price,
                    )

            # Обновляем статистику клиента
            customer.update_statistics()

            # Создаем историю взаимодействия клиента с магазином
            from customers.models import CustomerShopHistory

            history, created = CustomerShopHistory.objects.get_or_create(
                customer=customer, shop=request.current_shop
            )
            if not created:
                history.visits_count += 1
                history.save(update_fields=["visits_count", "last_visit"])

            # Загружаем заказ с полными данными для ответа
            order = _with_order_relations(Order.objects.all()).get(id=order.id)

            return 201, order

    except Http404 as e:
        return 400, {"error": str(e) or "Некорректные данные заказа"}
    except Exception as e:
        return 400, {"error": str(e)}


@router.put(
    "/{order_id}", response={200: OrderSchema, 400: ErrorSchema, 404: ErrorSchema}
)
def update_order(request, order_id: int, data: OrderUpdateSchema):
    """Обновление заказа"""
    if not request.auth.has_permission("orders.change_order"):
        raise PermissionError("Нет прав для изменения заказов")

    try:
        order = _get_accessible_order(request, order_id)
        old_status = order.status
        incoming = data.dict(exclude_unset=True)
        status_comment = incoming.pop("status_comment", "") or ""

        # Специальная проверка для изменения статуса
        if data.status and data.status != old_status:
            if not request.auth.has_permission("orders.change_status"):
                raise PermissionError("Нет прав для изменения статуса заказа")
            if data.status == "completed":
                new_final_cost = incoming.get("final_cost")
                if new_final_cost is None and order.final_cost is None:
                    return 400, {
                        "error": (
                            "Нельзя закрыть заказ без итоговой стоимости "
                            "(final_cost)"
                        )
                    }

        # Обновляем только переданные поля
        update_fields = []
        for field, value in incoming.items():
            if field == "assigned_to_id":
                if value:
                    assigned_user = get_object_or_404(User, id=value)
                    if not assigned_user.can_access_shop(order.shop):
                        return 400, {
                            "error": ("Исполнитель не привязан к филиалу этого заказа")
                        }
                    order.assigned_to = assigned_user
                else:
                    order.assigned_to = None
                update_fields.append("assigned_to")
            else:
                setattr(order, field, value)
                update_fields.append(field)

        # Автоматически устанавливаем дату завершения
        if data.status == "completed" and not order.completed_at:
            from django.utils import timezone

            order.completed_at = timezone.now()
            update_fields.append("completed_at")

        order.save(update_fields=update_fields + ["updated_at"])
        if data.status and data.status != old_status:
            _record_status_history(
                order=order,
                old_status=old_status,
                new_status=order.status,
                user=request.auth,
                comment=status_comment,
            )
        elif update_fields:
            _log_order_audit(
                order=order,
                action=OrderAuditLog.ActionChoices.UPDATED,
                actor=request.auth,
                message="Заказ обновлен",
                changes={"fields": update_fields},
            )

        # Обновляем статистику клиента если изменилась стоимость
        if "final_cost" in update_fields:
            order.customer.update_statistics()

        # Загружаем заказ с полными данными для ответа
        order = _with_order_relations(Order.objects.all()).get(id=order.id)

        return order

    except Http404:
        return 404, {"error": "Заказ не найден"}
    except Exception as e:
        return 400, {"error": str(e)}


@router.get(
    "/{order_id}/status-history",
    response=List[OrderStatusHistorySchema],
)
def list_status_history(request, order_id: int):
    """История статусов заказа."""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    order = _get_accessible_order(request, order_id)
    return order.status_history.select_related("changed_by").all()


@router.get("/{order_id}/audit-log", response=List[OrderAuditLogSchema])
def list_audit_log(request, order_id: int):
    """Журнал важных действий по заказу."""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    order = _get_accessible_order(request, order_id)
    return order.audit_logs.select_related("actor").all()


@router.get("/{order_id}/repair-stages", response=List[RepairStageSchema])
def list_repair_stages(request, order_id: int):
    """Этапы ремонта с фотофиксацией."""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    order = _get_accessible_order(request, order_id)
    return order.repair_stages.select_related("created_by").all()


@router.post(
    "/{order_id}/repair-stages",
    response={201: RepairStageSchema, 400: ErrorSchema},
)
def create_repair_stage(
    request,
    order_id: int,
    title: str = Form(...),
    description: str = Form(""),
    customer_visible: bool = Form(True),
    photo: UploadedFile | None = File(None),
):
    """Добавить произвольный этап ремонта, например с фото до/после работы."""
    if not request.auth.has_permission("orders.change_order"):
        raise PermissionError("Нет прав для изменения заказов")

    order = _get_accessible_order(request, order_id)
    clean_title = title.strip()
    if not clean_title:
        return 400, {"error": "Название этапа обязательно"}

    stage = RepairStage.objects.create(
        order=order,
        title=clean_title,
        description=description.strip(),
        customer_visible=customer_visible,
        photo=photo,
        created_by=request.auth,
    )
    _log_order_audit(
        order=order,
        action=OrderAuditLog.ActionChoices.STAGE_ADDED,
        actor=request.auth,
        message=f"Добавлен этап ремонта: {stage.title}",
        changes={"stage_id": stage.id, "customer_visible": customer_visible},
    )
    return 201, stage


@router.put(
    "/{order_id}/repair-stages/{stage_id}",
    response={200: RepairStageSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def update_repair_stage(
    request,
    order_id: int,
    stage_id: int,
    data: RepairStageUpdateSchema,
):
    """Обновить описание этапа или его видимость клиенту."""
    if not request.auth.has_permission("orders.change_order"):
        raise PermissionError("Нет прав для изменения заказов")

    order = _get_accessible_order(request, order_id)
    stage = order.repair_stages.filter(id=stage_id).first()
    if not stage:
        return 404, {"error": "Этап ремонта не найден"}

    update_fields = []
    for field, value in data.dict(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip()
        if field == "title" and not value:
            return 400, {"error": "Название этапа обязательно"}
        setattr(stage, field, value)
        update_fields.append(field)

    if update_fields:
        stage.save(update_fields=update_fields + ["updated_at"])
        _log_order_audit(
            order=order,
            action=OrderAuditLog.ActionChoices.STAGE_UPDATED,
            actor=request.auth,
            message=f"Обновлен этап ремонта: {stage.title}",
            changes={"stage_id": stage.id, "fields": update_fields},
        )

    return stage


@router.get("/{order_id}/approvals", response=List[OrderApprovalSchema])
def list_order_approvals(request, order_id: int):
    """Согласования цены и работ по заказу."""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    order = _get_accessible_order(request, order_id)
    return order.approvals.select_related("requested_by").all()


@router.post(
    "/{order_id}/approvals",
    response={201: OrderApprovalSchema, 400: ErrorSchema},
)
def request_order_approval(
    request,
    order_id: int,
    data: OrderApprovalCreateSchema,
):
    """Запросить у клиента согласование диагностики, работ или суммы."""
    if not request.auth.has_permission("orders.change_order"):
        raise PermissionError("Нет прав для изменения заказов")

    order = _get_accessible_order(request, order_id)
    title = data.title.strip()
    if not title:
        return 400, {"error": "Название согласования обязательно"}
    if data.amount < 0:
        return 400, {"error": "Сумма согласования не может быть отрицательной"}

    approval = OrderApproval.objects.create(
        order=order,
        title=title,
        description=(data.description or "").strip(),
        amount=data.amount,
        requested_by=request.auth,
    )
    _log_order_audit(
        order=order,
        action=OrderAuditLog.ActionChoices.APPROVAL_REQUESTED,
        actor=request.auth,
        message=f"Запрошено согласование: {approval.title}",
        changes={"approval_id": approval.id, "amount": float(approval.amount)},
    )
    return 201, approval
