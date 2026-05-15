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
- `db-backup` делает ежедневный `pg_dump` в Docker volume `backup_data`,
  может добавлять архив `media_data` и синхронизировать бэкапы через rclone.
- `health-monitor` регулярно проверяет frontend/backend и может отправлять
  webhook-alert при деградации.

## Запуск вручную

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

## CI/CD деплой

Основной pipeline находится в `.github/workflows/ci.yml`.
На `push` в `main`/`master` он выполняет backend tests, frontend tests/build,
проверяет production compose и после этого запускает деплой через
`scripts/deploy-production.sh`.

Для GitHub Actions нужны repository secrets:

```text
PRODUCTION_HOST=130.49.151.251
PRODUCTION_USER=root
PRODUCTION_PATH=/opt/repaircrm/crm
PRODUCTION_DOMAIN=b00bs.ru
PRODUCTION_SSH_KEY=<private ssh key with server access>
```

Тот же деплой можно запустить локально:

```bash
DEPLOY_HOST=130.49.151.251 \
DEPLOY_USER=root \
DEPLOY_PATH=/opt/repaircrm/crm \
DEPLOY_DOMAIN=b00bs.ru \
./scripts/deploy-production.sh
```

Скрипт синхронизирует код через `rsync`, сохраняет серверный
`.env.production`, выполняет `docker compose up -d --build --remove-orphans`,
затем проверяет Django и `/api/health`.

## Бэкапы PostgreSQL

Сервис `db-backup` запускается вместе с production compose и по умолчанию раз в
сутки создает custom-format dump в volume `backup_data`. Также он может
архивировать `media_data` и отправлять бэкапы во внешний storage через rclone.
Периодичность и срок хранения меняются через:

```env
POSTGRES_BACKUP_INTERVAL_SECONDS=86400
POSTGRES_BACKUP_RETENTION_DAYS=14
BACKUP_INCLUDE_MEDIA=true
```

Проверить файлы:

```bash
docker compose --env-file .env -f docker-compose.yml exec -T db-backup \
  sh -lc 'ls -lah /backups'
```

Offsite-копирование включается, когда задан `BACKUP_RCLONE_REMOTE`.
`RCLONE_CONFIG_B64` должен содержать base64 от `rclone.conf`.

```env
BACKUP_RCLONE_REMOTE=s3:repaircrm-backups/prod
BACKUP_SYNC_MAX_AGE=48h
RCLONE_CONFIG_B64=<base64-rclone-conf>
```

Пример подготовки конфига:

```bash
base64 -w0 ~/.config/rclone/rclone.conf
```

Восстановление в пустую БД:

```bash
docker compose --env-file .env -f docker-compose.yml exec -T db-backup \
  sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /backups/<dump-file>.dump'
```

## Health monitor и alerts

`health-monitor` проверяет цели из `MONITOR_TARGETS`. Формат:
`name=url`, несколько целей разделяются пробелом.

```env
MONITOR_TARGETS=frontend=http://frontend/ backend=http://backend:8000/api/health
MONITOR_INTERVAL_SECONDS=60
MONITOR_TIMEOUT_SECONDS=10
MONITOR_FAILURE_THRESHOLD=3
MONITOR_HOST_HEADER=b00bs.ru
MONITOR_FORWARDED_PROTO=https
ALERT_WEBHOOK_URL=
```

`ALERT_WEBHOOK_URL` может быть Slack/Discord/Telegram bridge или любой внутренний
webhook, принимающий JSON с полем `text`. Если URL пустой, мониторинг работает
только в логах контейнера.

`MONITOR_HOST_HEADER` нужен для прямой проверки backend-контейнера: Django
отклоняет неизвестные hostnames, поэтому мониторинг должен ходить с доменным
именем из `ALLOWED_HOSTS`.

`MONITOR_FORWARDED_PROTO=https` нужен после включения
`SECURE_SSL_REDIRECT=True`, чтобы внутренняя проверка не получала redirect.

## Перед реальным публичным запуском

- TLS на внешнем reverse proxy должен прокидывать `X-Forwarded-Proto`.
  После проверки домена можно включать `SECURE_SSL_REDIRECT=True` и
  `SECURE_HSTS_SECONDS=31536000`.
- Подключить внешний offsite-copy через `BACKUP_RCLONE_REMOTE` и проверить
  восстановление из удаленного dump.
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
