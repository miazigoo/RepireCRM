from typing import List

from django.db import models, transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import PageNumberPagination, paginate

from customers.models import Customer
from device.models import Device, DeviceModel
from Schemas.common import ErrorSchema, MessageSchema
from users.models import User

from .models import AdditionalService, Order, OrderService, RepairService
from .orders_schemas import (
    AdditionalServiceSchema,
    OrderCreateSchema,
    OrderFilterSchema,
    OrderListSchema,
    OrderSchema,
    OrderUpdateSchema,
)
from .schemas_repair_services import RepairServiceSchema

router = Router(tags=["Заказы"])


class OrderPagination(PageNumberPagination):
    page_size = 20


@router.get("/", response=List[OrderSchema])
@paginate(OrderPagination)
def list_orders(request, filters: OrderFilterSchema = Query(...)):
    """Получение списка заказов"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    # Базовый queryset с оптимизацией запросов
    queryset = Order.objects.select_related(
        "customer",
        "device__model__brand",
        "device__model__device_type",
        "shop",
        "created_by",
        "assigned_to",
    ).prefetch_related(
        Prefetch(
            "orderservice_set", queryset=OrderService.objects.select_related("service")
        )
    )

    # Фильтрация по магазинам в зависимости от прав
    if not request.auth.has_permission("orders.view_all_shops"):
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(shop__in=available_shops)
    elif hasattr(request, "current_shop") and request.current_shop:
        queryset = queryset.filter(shop=request.current_shop)

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


@router.get("/{order_id}", response=OrderSchema)
def get_order(request, order_id: int):
    """Получение заказа по ID"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра заказов")

    queryset = Order.objects.select_related(
        "customer",
        "device__model__brand",
        "device__model__device_type",
        "shop",
        "created_by",
        "assigned_to",
    ).prefetch_related(
        Prefetch(
            "orderservice_set", queryset=OrderService.objects.select_related("service")
        )
    )

    order = get_object_or_404(queryset, id=order_id)

    # Проверяем доступ к магазину заказа
    if not request.auth.can_access_shop(order.shop):
        raise PermissionError("Нет доступа к данному заказу")

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
                model=device_model, **data.device.dict(exclude={"model_id"})
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

            # Добавляем дополнительные услуги
            if data.additional_services:
                for service_data in data.additional_services:
                    service = get_object_or_404(
                        AdditionalService, id=service_data["service_id"]
                    )
                    OrderService.objects.create(
                        order=order,
                        service=service,
                        quantity=service_data.get("quantity", 1),
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
            order = (
                Order.objects.select_related(
                    "customer",
                    "device__model__brand",
                    "device__model__device_type",
                    "shop",
                    "created_by",
                    "assigned_to",
                )
                .prefetch_related(
                    Prefetch(
                        "orderservice_set",
                        queryset=OrderService.objects.select_related("service"),
                    )
                )
                .get(id=order.id)
            )

            return 201, order

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
        order = get_object_or_404(Order, id=order_id)

        # Проверяем доступ к магазину заказа
        if not request.auth.can_access_shop(order.shop):
            raise PermissionError("Нет доступа к данному заказу")

        # Специальная проверка для изменения статуса
        if data.status and data.status != order.status:
            if not request.auth.has_permission("orders.change_status"):
                raise PermissionError("Нет прав для изменения статуса заказа")
            if data.status == "completed":
                incoming = data.dict(exclude_unset=True)
                new_final_cost = incoming.get("final_cost")
                if new_final_cost is None and order.final_cost is None:
                    return 400, {
                        "error": "Нельзя закрыть заказ без итоговой стоимости (final_cost)"
                    }

        # Обновляем только переданные поля
        update_fields = []
        for field, value in data.dict(exclude_unset=True).items():
            if field == "assigned_to_id":
                if value:
                    assigned_user = get_object_or_404(User, id=value)
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

        # Обновляем статистику клиента если изменилась стоимость
        if "final_cost" in update_fields:
            order.customer.update_statistics()

        # Загружаем заказ с полными данными для ответа
        order = (
            Order.objects.select_related(
                "customer",
                "device__model__brand",
                "device__model__device_type",
                "shop",
                "created_by",
                "assigned_to",
            )
            .prefetch_related(
                Prefetch(
                    "orderservice_set",
                    queryset=OrderService.objects.select_related("service"),
                )
            )
            .get(id=order.id)
        )

        return order

    except Order.DoesNotExist:
        return 404, {"error": "Заказ не найден"}
    except Exception as e:
        return 400, {"error": str(e)}


@router.get("/additional-services", response=List[AdditionalServiceSchema])
def list_additional_services(request):
    """Получение списка дополнительных услуг"""
    if not request.auth.has_permission("orders.view_order"):
        raise PermissionError("Нет прав для просмотра услуг")

    queryset = AdditionalService.objects.filter(is_active=True)

    # Фильтруем по доступным в текущем магазине
    if hasattr(request, "current_shop") and request.current_shop:
        queryset = queryset.filter(
            Q(shops__isnull=True) | Q(shops=request.current_shop)
        ).distinct()

    return queryset.order_by("category", "name")


@router.get("/statistics", response=dict)
def get_orders_statistics(request):
    """Получение статистики по заказам"""
    if not request.auth.has_permission("reports.view_analytics"):
        raise PermissionError("Нет прав для просмотра аналитики")

    from datetime import timedelta

    from django.db.models import Avg, Count, Sum
    from django.utils import timezone

    # Базовый queryset с учетом прав доступа
    queryset = Order.objects.all()
    if not request.auth.has_permission("orders.view_all_shops"):
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(shop__in=available_shops)
    elif hasattr(request, "current_shop") and request.current_shop:
        queryset = queryset.filter(shop=request.current_shop)

    # Статистика за последние 30 дней
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_orders = queryset.filter(created_at__gte=thirty_days_ago)

    # Общая статистика
    total_stats = queryset.aggregate(
        total_orders=Count("id"),
        total_revenue=Sum("final_cost"),
        avg_order_value=Avg("final_cost"),
    )

    # Статистика за последние 30 дней
    recent_stats = recent_orders.aggregate(
        recent_orders=Count("id"), recent_revenue=Sum("final_cost")
    )

    # Статистика по статусам
    status_stats = (
        queryset.values("status").annotate(count=Count("id")).order_by("-count")
    )

    return {
        "total_orders": total_stats["total_orders"] or 0,
        "total_revenue": float(total_stats["total_revenue"] or 0),
        "avg_order_value": float(total_stats["avg_order_value"] or 0),
        "recent_orders": recent_stats["recent_orders"] or 0,
        "recent_revenue": float(recent_stats["recent_revenue"] or 0),
        "status_distribution": list(status_stats),
        "period": "30 days",
    }


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
