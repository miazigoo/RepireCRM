from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from customers.models import Customer
from Schemas.customers.customers import (
    CustomerSchema, CustomerCreateSchema, CustomerUpdateSchema,
    CustomerListSchema, CustomerFilterSchema
)
from Schemas.common import MessageSchema, ErrorSchema
from typing import List

router = Router(tags=["Клиенты"])


class CustomerPagination(PageNumberPagination):
    page_size = 20


@router.get("/", response=List[CustomerSchema])
@paginate(CustomerPagination)
def list_customers(request, filters: CustomerFilterSchema = Query(...)):
    """Получение списка клиентов"""
    # Проверяем права доступа
    if not request.auth.has_permission('customers.view_customer'):
        raise PermissionError("Нет прав для просмотра клиентов")

    queryset = Customer.objects.select_related('created_by').all()

    # Применяем фильтры
    if filters.search:
        queryset = queryset.filter(
            Q(first_name__icontains=filters.search) |
            Q(last_name__icontains=filters.search) |
            Q(phone__icontains=filters.search) |
            Q(email__icontains=filters.search)
        )

    if filters.source:
        queryset = queryset.filter(source=filters.source)

    if filters.created_from:
        queryset = queryset.filter(created_at__date__gte=filters.created_from)

    if filters.created_to:
        queryset = queryset.filter(created_at__date__lte=filters.created_to)

    if filters.has_orders is not None:
        if filters.has_orders:
            queryset = queryset.filter(orders_count__gt=0)
        else:
            queryset = queryset.filter(orders_count=0)

    return queryset.order_by('-created_at')


@router.get("/{customer_id}", response=CustomerSchema)
def get_customer(request, customer_id: int):
    """Получение клиента по ID"""
    if not request.auth.has_permission('customers.view_customer'):
        raise PermissionError("Нет прав для просмотра клиентов")

    customer = get_object_or_404(Customer, id=customer_id)
    return customer


@router.post("/", response={201: CustomerSchema, 400: ErrorSchema})
def create_customer(request, data: CustomerCreateSchema):
    """Создание нового клиента"""
    if not request.auth.has_permission('customers.add_customer'):
        raise PermissionError("Нет прав для создания клиентов")

    try:
        # Проверяем уникальность телефона
        if Customer.objects.filter(phone=data.phone).exists():
            return 400, {"error": "Клиент с таким номером телефона уже существует"}

        customer = Customer.objects.create(
            **data.dict(),
            created_by=request.auth
        )

        # Создаем историю взаимодействия с текущим магазином
        if hasattr(request, 'current_shop'):
            from customers.models import CustomerShopHistory
            CustomerShopHistory.objects.get_or_create(
                customer=customer,
                shop=request.current_shop
            )

        return 201, customer

    except Exception as e:
        return 400, {"error": str(e)}


@router.put("/{customer_id}", response={200: CustomerSchema, 400: ErrorSchema, 404: ErrorSchema})
def update_customer(request, customer_id: int, data: CustomerUpdateSchema):
    """Обновление клиента"""
    if not request.auth.has_permission('customers.change_customer'):
        raise PermissionError("Нет прав для изменения клиентов")

    try:
        customer = get_object_or_404(Customer, id=customer_id)

        # Проверяем уникальность телефона (если он изменился)
        if data.phone and data.phone != customer.phone:
            if Customer.objects.filter(phone=data.phone).exclude(id=customer_id).exists():
                return 400, {"error": "Клиент с таким номером телефона уже существует"}

        # Обновляем только переданные поля
        for field, value in data.dict(exclude_unset=True).items():
            setattr(customer, field, value)

        customer.save()
        return customer

    except Customer.DoesNotExist:
        return 404, {"error": "Клиент не найден"}
    except Exception as e:
        return 400, {"error": str(e)}


@router.delete("/{customer_id}", response={200: MessageSchema, 403: ErrorSchema, 404: ErrorSchema})
def delete_customer(request, customer_id: int):
    """Удаление клиента"""
    if not request.auth.has_permission('customers.delete_customer'):
        raise PermissionError("Нет прав для удаления клиентов")

    try:
        customer = get_object_or_404(Customer, id=customer_id)

        # Проверяем, есть ли у клиента заказы
        if customer.orders_count > 0:
            return 403, {"error": "Нельзя удалить клиента с существующими заказами"}

        customer.delete()
        return {"message": "Клиент успешно удален"}

    except Customer.DoesNotExist:
        return 404, {"error": "Клиент не найден"}


@router.get("/{customer_id}/orders", response=List[dict])
def get_customer_orders(request, customer_id: int):
    """Получение заказов клиента"""
    if not request.auth.has_permission('customers.view_customer'):
        raise PermissionError("Нет прав для просмотра клиентов")

    customer = get_object_or_404(Customer, id=customer_id)

    # Получаем заказы клиента с учетом прав доступа к магазинам
    from orders.models import Order
    queryset = Order.objects.filter(customer=customer)

    if not request.auth.has_permission('orders.view_all_shops'):
        # Показываем только заказы из доступных магазинов
        available_shops = request.auth.get_available_shops()
        queryset = queryset.filter(shop__in=available_shops)

    orders = queryset.select_related(
        'device__model__brand', 'device__model__device_type',
        'shop', 'created_by', 'assigned_to'
    ).order_by('-created_at')

    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "device": f"{order.device.model.brand.name} {order.device.model.name}",
            "cost_estimate": float(order.cost_estimate),
            "final_cost": float(order.final_cost) if order.final_cost else None,
            "created_at": order.created_at,
            "shop": order.shop.name
        }
        for order in orders
    ]