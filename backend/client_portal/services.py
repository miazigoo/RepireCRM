from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from phonenumber_field.phonenumber import PhoneNumber

from customers.models import Customer, CustomerShopHistory
from device.models import Device, DeviceBrand, DeviceModel, DeviceType
from orders.models import Order
from shops.models import Shop
from users.models import User

from .schemas import PortalOrderCreateSchema, PortalRegisterSchema

CUSTOMER_TOKEN_DAYS = 30
PORTAL_ORDER_USERNAME = "portal-intake"


class PortalError(ValueError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.details = details or {}
        super().__init__(message)


def normalize_phone(phone: str) -> str:
    parsed = PhoneNumber.from_string(phone, region="RU")
    if not parsed.is_valid():
        raise PortalError("Укажите корректный номер телефона")
    return parsed.as_e164


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise PortalError("Пароль должен быть не короче 8 символов")
    if password.isdigit() or password.isalpha():
        raise PortalError("Пароль должен содержать разные типы символов")


def issue_customer_token(customer: Customer) -> str:
    now = datetime.utcnow()
    payload = {
        "customer_id": customer.id,
        "scope": "customer",
        "exp": now + timedelta(days=CUSTOMER_TOKEN_DAYS),
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def register_customer(data: PortalRegisterSchema) -> Customer:
    phone = normalize_phone(data.phone)
    validate_password(data.password)

    with transaction.atomic():
        customer = Customer.objects.filter(phone=phone).first()
        if customer and customer.has_portal_password:
            raise PortalError("Клиент с таким телефоном уже зарегистрирован")

        if not customer:
            customer = Customer(phone=phone)

        customer.first_name = data.first_name.strip()
        customer.last_name = data.last_name.strip()
        customer.email = data.email or ""
        customer.marketing_consent = data.marketing_consent
        customer.portal_password = make_password(data.password)
        customer.portal_is_active = True
        customer.portal_registered_at = timezone.now()
        customer.full_clean(exclude=["created_by"])
        customer.save()
        return customer


def authenticate_customer(phone: str, password: str) -> Customer:
    normalized_phone = normalize_phone(phone)
    customer = Customer.objects.filter(phone=normalized_phone).first()
    if (
        customer is None
        or not customer.portal_is_active
        or not customer.portal_password
        or not check_password(password, customer.portal_password)
    ):
        raise PortalError("Неверный телефон или пароль")

    customer.portal_last_login_at = timezone.now()
    customer.save(update_fields=["portal_last_login_at"])
    return customer


def get_customer_from_token(token: str) -> Customer | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

    if payload.get("scope") != "customer":
        return None

    customer_id = payload.get("customer_id")
    try:
        return Customer.objects.get(id=customer_id, portal_is_active=True)
    except Customer.DoesNotExist:
        return None


def get_default_shop() -> Shop:
    code = getattr(settings, "PORTAL_DEFAULT_SHOP_CODE", "")
    queryset = Shop.objects.filter(is_active=True)
    shop = queryset.filter(code=code).first() if code else queryset.first()
    if not shop:
        raise PortalError("Сервис временно не принимает онлайн-заявки")
    return shop


def get_portal_intake_user(shop: Shop) -> User:
    user, _ = User.objects.get_or_create(
        username=PORTAL_ORDER_USERNAME,
        defaults={
            "first_name": "Online",
            "last_name": "Portal",
            "email": "portal@repair-crm.local",
            "is_active": False,
        },
    )
    if user.current_shop_id != shop.id:
        user.current_shop = shop
        user.save(update_fields=["current_shop"])
    user.shops.add(shop)
    return user


def create_customer_order(customer: Customer, data: PortalOrderCreateSchema) -> Order:
    if data.cost_estimate < 0:
        raise PortalError("Предварительная стоимость не может быть отрицательной")

    with transaction.atomic():
        shop = get_default_shop()
        intake_user = get_portal_intake_user(shop)

        brand, _ = DeviceBrand.objects.get_or_create(name=data.brand.strip())
        device_type, _ = DeviceType.objects.get_or_create(name=data.device_type.strip())
        model, _ = DeviceModel.objects.get_or_create(
            brand=brand,
            device_type=device_type,
            name=data.model_name.strip(),
        )
        device = Device.objects.create(
            model=model,
            serial_number=data.serial_number or "",
            imei=data.imei or "",
            color=data.color or "",
            storage_capacity=data.storage_capacity or "",
        )

        order = Order.objects.create(
            shop=shop,
            customer=customer,
            device=device,
            problem_description=data.problem_description.strip(),
            accessories=data.accessories or "",
            device_condition=data.device_condition or "",
            cost_estimate=Decimal(str(data.cost_estimate)),
            created_by=intake_user,
            notes="Заявка создана клиентом из личного кабинета.",
        )

        history, created = CustomerShopHistory.objects.get_or_create(
            customer=customer,
            shop=shop,
        )
        if not created:
            history.visits_count += 1
            history.save(update_fields=["visits_count", "last_visit"])

        customer.update_statistics()
        return order


def serialize_portal_order(order: Order) -> dict[str, Any]:
    device = order.device
    model = device.model
    title_parts = [model.brand.name, model.name]
    if device.color:
        title_parts.append(device.color)
    if device.storage_capacity:
        title_parts.append(device.storage_capacity)

    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "status_display": order.get_status_display(),
        "priority": order.priority,
        "device_title": " ".join(title_parts),
        "problem_description": order.problem_description,
        "diagnosis": order.diagnosis or None,
        "work_description": order.work_description or None,
        "cost_estimate": float(order.cost_estimate),
        "final_cost": float(order.final_cost) if order.final_cost is not None else None,
        "remaining_payment": float(order.remaining_payment),
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "estimated_completion": order.estimated_completion,
    }


def ensure_customer_payload(data: PortalOrderCreateSchema) -> None:
    required = {
        "device_type": data.device_type,
        "brand": data.brand,
        "model_name": data.model_name,
        "problem_description": data.problem_description,
    }
    missing = [field for field, value in required.items() if not value.strip()]
    if missing:
        raise PortalError("Заполните обязательные поля", {"fields": missing})

    if data.imei and not data.imei.isdigit():
        raise PortalError("IMEI должен содержать только цифры", {"field": "imei"})
    if data.imei and len(data.imei) not in (14, 15):
        raise PortalError("IMEI должен содержать 14 или 15 цифр", {"field": "imei"})


def portal_error_response(exc: Exception) -> tuple[int, dict[str, Any]]:
    if isinstance(exc, PortalError):
        return 400, {"error": str(exc), "details": exc.details}
    if isinstance(exc, ValidationError):
        return 400, {"error": "Ошибка валидации", "details": exc.message_dict}
    return 400, {"error": "Не удалось выполнить операцию"}
