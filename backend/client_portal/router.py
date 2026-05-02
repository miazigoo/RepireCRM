from typing import List

from django.db.models import QuerySet
from django_ratelimit.decorators import ratelimit
from ninja import Router
from ninja.security import HttpBearer

from customers.models import Customer
from orders.models import Order

from .schemas import (
    PortalCustomerSchema,
    PortalErrorSchema,
    PortalLoginSchema,
    PortalOrderCreateSchema,
    PortalOrderSchema,
    PortalRegisterSchema,
    PortalTokenSchema,
)
from .services import (
    CUSTOMER_TOKEN_DAYS,
    authenticate_customer,
    create_customer_order,
    ensure_customer_payload,
    get_customer_from_token,
    issue_customer_token,
    portal_error_response,
    register_customer,
    serialize_portal_order,
)

router = Router(tags=["Кабинет клиента"], auth=None)


class CustomerAuthBearer(HttpBearer):
    def authenticate(self, request, token):
        return get_customer_from_token(token)


def _customer_payload(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "phone": str(customer.phone),
        "email": customer.email or None,
    }


def _order_queryset(customer: Customer) -> QuerySet[Order]:
    return Order.objects.filter(customer=customer).select_related(
        "device__model__brand",
        "device__model__device_type",
    )


@router.post(
    "/auth/register",
    response={201: PortalTokenSchema, 400: PortalErrorSchema},
)
@ratelimit(key="ip", rate="10/m", block=True)
def register(request, data: PortalRegisterSchema):
    try:
        customer = register_customer(data)
    except Exception as exc:
        return portal_error_response(exc)

    return 201, {
        "access_token": issue_customer_token(customer),
        "expires_in": CUSTOMER_TOKEN_DAYS * 24 * 60 * 60,
        "customer": _customer_payload(customer),
    }


@router.post("/auth/login", response={200: PortalTokenSchema, 400: PortalErrorSchema})
@ratelimit(key="ip", rate="10/m", block=True)
def login(request, data: PortalLoginSchema):
    try:
        customer = authenticate_customer(data.phone, data.password)
    except Exception as exc:
        return portal_error_response(exc)

    return {
        "access_token": issue_customer_token(customer),
        "expires_in": CUSTOMER_TOKEN_DAYS * 24 * 60 * 60,
        "customer": _customer_payload(customer),
    }


@router.get(
    "/me",
    response=PortalCustomerSchema,
    auth=CustomerAuthBearer(),
)
def me(request):
    return _customer_payload(request.auth)


@router.get(
    "/orders",
    response=List[PortalOrderSchema],
    auth=CustomerAuthBearer(),
)
def list_orders(request):
    orders = _order_queryset(request.auth).order_by("-created_at")
    return [serialize_portal_order(order) for order in orders]


@router.post(
    "/orders",
    response={201: PortalOrderSchema, 400: PortalErrorSchema},
    auth=CustomerAuthBearer(),
)
def create_order(request, data: PortalOrderCreateSchema):
    try:
        ensure_customer_payload(data)
        order = create_customer_order(request.auth, data)
    except Exception as exc:
        return portal_error_response(exc)

    return 201, serialize_portal_order(order)


@router.get(
    "/orders/{order_id}",
    response={200: PortalOrderSchema, 404: PortalErrorSchema},
    auth=CustomerAuthBearer(),
)
def get_order(request, order_id: int):
    order = _order_queryset(request.auth).filter(id=order_id).first()
    if order is None:
        return 404, {"error": "Заказ не найден"}
    return serialize_portal_order(order)
