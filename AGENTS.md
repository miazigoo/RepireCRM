# AGENTS.md - Repair CRM AI Development Guide

This guide provides essential knowledge for AI agents to be immediately productive in the RepireCRM codebase.

## Architecture Overview

**Tech Stack**: Django >=5 API (django-ninja; dev image currently runs Django 6.x) + Angular frontend + PostgreSQL + Redis + Celery

**Multi-Shop Architecture**: This is a **multi-tenant SaaS application** where every request is scoped to a `Shop` instance. The shop context flows through:
- `x-current-shop` HTTP header → extracted in `AuthBearer.authenticate()` at `backend/core/api_app.py`
- Attached to `request.current_shop` via `ShopMiddleware` (`backend/core/middleware.py`)
- User permissions filtered by `can_access_shop(shop)` method on User model
- ALL queries must be shop-aware (filter, validate shop ownership before operations)

**API Routes Pattern**:
```python
# backend/core/api_app.py defines main NinjaAPI
api = NinjaAPI(auth=AuthBearer())  # JWT-based auth
api.add_router("/endpoint", router)  # Routers added from each app
```
Each app (customers, orders, inventory, etc.) has `router.py` that uses `@router.get/post/put/delete()` with Ninja Schemas.

## Key Data Flows & Models

### Core Models (interconnected):
- **Shop** (`shops/models.py`): Tenant isolation root. Every entity must reference a Shop.
- **User** (`users/models.py`): Custom AbstractUser with roles, phone, multiple shop access via UserShop M2M
- **Order** (`orders/models.py`): Repair orders with StatusChoices (RECEIVED→DIAGNOSED→WAITING_PARTS→IN_REPAIR→TESTING→READY→COMPLETED, plus CANCELLED), audit logging
- **Customer** (`customers/models.py`): Shared client profiles with source tracking and per-shop interaction history
- **Device** (`device/models.py`): Device models with Brand/Model/Type hierarchy
- **InventoryItem** (`inventory/models.py`): Parts warehouse with multi-shop StockBalance, barcode tracking, price history
- **Finance**: CashRegister, Payment, PaymentMethod for transactions

### Signal Handlers (Auto-side-effects):
- `inventory/signals.py`: When InventoryItem created → auto-creates StockBalance for ALL shops, price history entries
- On price changes → InventoryItemPriceHistory entries created automatically (pre_save hook)
- **Pattern**: Always check signal handlers before assuming manual DB operations needed

## Critical Patterns & Conventions

### 1. Permission System
```python
# All endpoints check permissions before business logic
if not request.auth.has_permission("customers.view_customer"):
    raise PermissionError("Нет прав для просмотра клиентов")
```
Permissions are stored in `users.models.Permission`, tied to `Role` via M2M.

### 2. Service Layer (Business Logic)
```python
# backend/inventory/services.py
class InventoryService:
    def receive_items_ad_hoc(self, shop, user, items: List[Dict], common_notes=""):
        # Complex multi-step operations wrapped in @transaction.atomic
```
Use service classes for multi-step operations with multiple DB queries. Always wrap in `@transaction.atomic()`.

### 3. API Schemas & Deserialization
```python
# backend/Schemas/common.py defines base schemas
# Each endpoint uses Input Schema (request) → Output Schema (response)
from ninja import Router, Query
@router.get("/", response=List[CustomerSchema])
def list_customers(request, filters: CustomerFilterSchema = Query(...)):
```
**Important**: Schemas use type hints, Ninja auto-validates. Filters use `Query()` for querystring params.

### 4. Pagination Pattern
```python
class CustomerPagination(PageNumberPagination):
    page_size = 20  # Default size

@paginate(CustomerPagination)
def list_customers(request, ...): ...
```
Returns decorated list as paginated response automatically.

### 5. Multi-Shop Safety
**Every endpoint must validate shop access**:
```python
def _get_accessible_order(request, order_id: int) -> Order:
    order = get_object_or_404(Order.objects.select_related(...), id=order_id)
    if not request.auth.can_access_shop(order.shop):
        raise PermissionError("Нет доступа к данному заказу")
    return order
```

### 6. Audit Logging
```python
# orders/router.py pattern
def _log_order_audit(order: Order, action: str, message: str, actor=None, changes: dict = None):
    OrderAuditLog.objects.create(order=order, action=action, actor=actor, ...)

def _record_status_history(order: Order, old_status: str, new_status: str, user=None):
    OrderStatusHistory.objects.create(...)
```
Use these for compliance - Order lifecycle has full audit trail.

### 7. Celery Tasks (Async Work)
```python
# backend/core/settings.py defines schedule
CELERY_BEAT_SCHEDULE = {
    "low-stock-scan-daily": {
        "task": "tasks.tasks.low_stock_scan",
        "schedule": 60 * 60 * 24,
    },
}
```
Redis is broker. Task modules in each app's `tasks.py`. For long operations, dispatch Celery task.

### 8. WebSocket/Notifications
```python
# backend/notifications/consumers.py
class NotificationConsumer(AsyncWebsocketConsumer):
    # Groups: user_{id}, shop_{id}, role_{code}
    # Broadcast to groups on DB changes
```
Use channels for real-time updates. Send via group_send after DB modifications.

## Developer Workflows

### Local Development
```bash
bash scripts/setup-dev.sh  # Bootstraps Docker, pre-commit hooks
docker compose -f docker-compose.dev.yml up  # Starts db, redis, backend, frontend
```

### Running Commands
```bash
# In running container or docker exec
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py shell

# Run tests
docker compose exec backend pytest tests/ -v --cov=backend

# Celery worker (separate container)
docker compose exec backend celery -A core worker -l info
```

### Code Quality
```bash
# Pre-commit hooks auto-run these:
black backend/  # Format (line-length=88)
isort backend/  # Import sorting (profile=black)
flake8 backend/  # Linting
mypy backend/  # Type checking (migrations excluded)
```
Config in `backend/pyproject.toml`.

### Database Migrations
```bash
python manage.py makemigrations app_name
python manage.py migrate
# Migrations go in {app}/migrations/. Always commit after makemigrations.
```

### Testing Pattern
```python
# backend/tests/test_orders.py
class OrderTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.shop = Shop.objects.create(...)

    def test_order_creation(self):
        order = Order.objects.create(shop=self.shop, ...)
        self.assertEqual(order.status, Order.StatusChoices.RECEIVED)
```
Use `TestCase` (transactional), factory_boy for fixtures (if using FactoryBoy). Always create Shop + User in setUp.

## Critical Integration Points

### Order → Inventory Flow
1. Order created (stock reserved via signals if needed)
2. Parts received from suppliers (StockMovement + StockBalance updated)
3. Order completed → inventory consumed via RetailSale
4. Low stock trigger Celery task (`tasks.tasks.low_stock_scan`)

### Notifications Pipeline
1. DB change (Order status update, Payment created, etc.)
2. Code calls `async_to_sync(channel_layer.group_send)(group_name, message)`
3. WebSocket consumer receives, broadcasts to connected users
4. Frontend updates real-time

### Authentication Flow
1. Frontend sends credentials → `/api/auth/login`
2. Returns JWT token (HS256, SECRET_KEY as key)
3. Frontend includes in `Authorization: Bearer {token}` header
4. `AuthBearer.authenticate()` decodes JWT, validates user, calls `_attach_current_shop()`
5. `request.auth` = User instance, `request.current_shop` = Shop instance

## File Structure by Responsibility

| Path | Purpose |
|------|---------|
| `backend/core/` | Django config, API setup, middleware |
| `backend/core/api_app.py` | NinjaAPI definition + auth handler |
| `backend/{app}/router.py` | HTTP endpoints for that module |
| `backend/{app}/models.py` | Data models + Meta, signals setup |
| `backend/{app}/services.py` | Business logic (reusable functions) |
| `backend/{app}/tasks.py` | Celery async tasks |
| `backend/{app}/consumers.py` | WebSocket handlers |
| `backend/Schemas/` | Shared + app-specific request/response schemas |
| `backend/tests/` | pytest test suite |
| `frontend/crm-app/` | Angular app (separate ecosystem) |
| `docker-compose.dev.yml` | Local dev environment |
| `scripts/setup-dev.sh` | One-time dev setup |

## Common Gotchas & Antipatterns

1. **Don't ignore Shop context**: Always verify shop ownership before CRUD
2. **Don't query without select_related()**: N+1 queries kill performance, always prefetch related objects
3. **Don't assume request.current_shop exists**: Check in middleware, may be None
4. **Don't forget audit logging**: Orders, Payments, Inventory changes must be logged
5. **Don't modify in signals without @transaction.atomic()**: Race conditions
6. **Don't hardcode "admin" shop logic**: Apps are shop-agnostic
7. **Don't write synchronous I/O in views**: Use Celery for emails, SMS, external APIs

## Example: Adding an Endpoint

```python
# 1. Define schema in app/schemas.py
from ninja import Schema
class ItemCreateSchema(Schema):
    name: str
    price: float

# 2. Add handler in app/router.py
from ninja import Router
router = Router(tags=["Items"])

@router.post("/", response=ItemSchema)
def create_item(request, payload: ItemCreateSchema):
    if not request.auth.has_permission("inventory.add_inventoryitem"):
        raise PermissionError()

    item = InventoryItem.objects.create(
        shop=request.current_shop,  # Always scope to shop
        name=payload.name,
        price=payload.price,
    )
    # If complex, dispatch to service layer
    return item

# 3. Add router in core/api_app.py
api.add_router("/items", items_router)

# 4. Test in tests/test_items.py
```

## Documentation References

- Django: https://docs.djangoproject.com/
- django-ninja: https://django-ninja.rest-framework.com/
- Celery: https://docs.celeryproject.org/
- Channels: https://channels.readthedocs.io/
- PostgreSQL: Use raw SQL only when ORM insufficient (rarely)
