# Production Checklist

## Что уже подготовлено

- `docker-compose.yml` поднимает PostgreSQL, Redis, backend на Gunicorn и frontend
  через nginx.
- nginx сохраняет путь `/api/*` при проксировании в Django и отдает Angular SPA
  через `try_files`.
- Django читает production security-настройки из env: `ALLOWED_HOSTS`,
  `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, cookie secure flags, HSTS,
  Sentry.
- Backend контейнер выполняет `migrate`, `collectstatic`, затем запускает
  `gunicorn`.
- Healthcheck backend проверяет `/api/health`.

## Запуск

1. Скопировать `.env.production.example` в `.env`.
2. Задать сильный `SECRET_KEY`, `POSTGRES_PASSWORD`, домены в `ALLOWED_HOSTS`,
   `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`. Оставить в `ALLOWED_HOSTS`
   `127.0.0.1` и `localhost`, они нужны внутреннему Docker healthcheck.
3. Запустить:

```bash
docker compose --env-file .env -f docker-compose.yml up -d --build
```

4. Проверить:

```bash
curl http://localhost/api/health
docker compose -f docker-compose.yml ps
```

## Перед реальным публичным запуском

- Поставить TLS на внешнем reverse proxy или включить HTTPS на edge.
- Включить `SECURE_SSL_REDIRECT=True` и `SECURE_HSTS_SECONDS=31536000` только
  после проверки HTTPS.
- Подключить бэкапы PostgreSQL и media volume.
- Подключить Sentry через `SENTRY_DSN`.
- Подключить ежедневный запуск проверки подписок:

```bash
docker compose --env-file .env -f docker-compose.yml exec -T backend \
  python manage.py check_subscriptions
```

- Настроить SMS/Email-провайдера для уведомлений по статусам.
- Завести первый филиал и роли через админку или management command.
