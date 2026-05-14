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
- Frontend nginx отдает SPA с security headers, immutable cache для
  хешированных assets и healthcheck.
- `db-backup` делает ежедневный `pg_dump` в Docker volume `backup_data`.

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

## Бэкапы PostgreSQL

Сервис `db-backup` запускается вместе с production compose и по умолчанию раз в
сутки создает custom-format dump в volume `backup_data`. Периодичность и срок
хранения меняются через:

```env
POSTGRES_BACKUP_INTERVAL_SECONDS=86400
POSTGRES_BACKUP_RETENTION_DAYS=14
```

Проверить файлы:

```bash
docker compose --env-file .env -f docker-compose.yml exec -T db-backup \
  sh -lc 'ls -lah /backups'
```

Восстановление в пустую БД:

```bash
docker compose --env-file .env -f docker-compose.yml exec -T db-backup \
  sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /backups/<dump-file>.dump'
```

## Перед реальным публичным запуском

- Поставить TLS на внешнем reverse proxy или включить HTTPS на edge.
- Включить `SECURE_SSL_REDIRECT=True` и `SECURE_HSTS_SECONDS=31536000` только
  после проверки HTTPS.
- Подключить внешний offsite-copy для `backup_data` и отдельный backup media
  volume.
- Подключить Sentry через `SENTRY_DSN`.
- Проверка подписок уже вынесена в сервис `subscription-checker` в
  `docker-compose.yml`. По умолчанию он запускает
  `python manage.py check_subscriptions` раз в сутки. Интервал можно изменить
  через `SUBSCRIPTION_CHECK_INTERVAL_SECONDS`.
- Для ручной проверки подписок:

```bash
docker compose --env-file .env -f docker-compose.yml exec -T backend \
  python manage.py check_subscriptions
```

- Настроить SMS/Email-провайдера для уведомлений по статусам.
- Завести первый филиал и роли через админку или management command.
