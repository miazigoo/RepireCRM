# Контракт синхронизации клиентского кабинета

Рабочая CRM остается основной системой для сотрудников. Внешний клиентский backend
хранит аккаунты клиентов, подтвержденные контакты, локальный снимок заказов и
исходящие действия клиента. Интеграция включается отдельно для каждой организации.
Если компании клиентская часть не нужна, интеграция остается выключенной и CRM не
делает внешних запросов.

## Настройка в CRM

API CRM:

- `GET /api/client-sync/status` - состояние интеграции текущей организации.
- `PUT /api/client-sync/integration` - включить/изменить внешний backend.
- `POST /api/client-sync/run` - ручной запуск push/pull.
- `GET /api/client-sync/actions` - последние действия клиента, принятые в CRM.

Обязательные поля интеграции:

- `enabled=true`
- `base_url`, например `https://client.company.ru`
- `api_key` - общий sync-токен для server-to-server запросов
- `tenant_key` - стабильный ключ компании во внешнем клиентском backend

## Авторизация sync API

CRM отправляет заголовки:

```http
X-Sync-Token: <api_key>
X-Tenant-Key: <tenant_key>
Content-Type: application/json
Accept: application/json
```

## Push заказов из CRM

CRM отправляет батч снимков:

`POST /api/sync/orders/upsert`

```json
{
  "tenant_key": "org-1",
  "sent_at": "2026-05-09T20:00:00+03:00",
  "orders": [
    {
      "crm_order_id": 123,
      "order_number": "ORD-MSK01-000123",
      "shop": {"crm_shop_id": 1, "code": "MSK01", "name": "Москва"},
      "customer": {
        "crm_customer_id": 77,
        "phone": "+79990000000",
        "email": "client@example.com"
      },
      "device": {"brand": "Apple", "model_name": "iPhone 14"},
      "status": "ready",
      "cost_estimate": "5000.00",
      "final_cost": null,
      "repair_stages": [],
      "approvals": []
    }
  ]
}
```

Ожидаемый ответ:

```json
{
  "orders": [
    {"crm_order_id": 123, "remote_order_id": "portal-order-abc"}
  ]
}
```

Деньги передаются строками decimal, чтобы не терять копейки.

## Pull действий клиента

CRM забирает ожидающие действия:

`GET /api/sync/actions?limit=100`

Ответ:

```json
{
  "actions": [
    {
      "id": "act-1001",
      "type": "approval.decided",
      "payload": {
        "crm_approval_id": 45,
        "status": "approved",
        "comment": "Согласен"
      }
    }
  ]
}
```

Поддержанные типы:

- `approval.decided` - клиент согласовал/отклонил работу.
- `repair_request.created` или `order.created` - клиент создал заявку.
- любой другой тип сохраняется как задача в CRM, чтобы действие не потерялось.

После обработки CRM подтверждает действие:

`POST /api/sync/actions/{id}/mark-synced`

```json
{
  "status": "applied",
  "crm_order_id": 123,
  "crm_task_id": null,
  "error": ""
}
```

## Запуск

Ручной запуск:

```bash
docker compose -f docker-compose.dev.yml exec -T backend python manage.py sync_client_portal
```

Планировщик может дергать Celery task:

```python
client_sync.tasks.sync_client_portals
```
