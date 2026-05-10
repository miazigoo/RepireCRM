# Production deployment

Сервер запускает два Docker-стека за хостовым Nginx:

| Стек | Docker project | Хост-порт | Домен |
|------|---------------|-----------|-------|
| Repair CRM | `repaircrm` | `8080` (frontend) | `b00bs.ru` |
| Client Portal | `repaircrm-client` | `8081` (frontend) | `repire-status.ru` |

Backend CRM (`8000/tcp`) и backend клиентского портала (`8040/tcp`) не
проксируются напрямую — все запросы к API идут через контейнерный nginx
каждого стека.

## Структура на сервере

```text
/opt/repaircrm/crm/           — репозиторий RepireCRM
/opt/repaircrm/client/        — репозиторий RepireCRM-Client
/opt/repaircrm/secrets/       — .env.production файлы (gitignored)
/etc/nginx/sites-enabled/repaircrm-sites.conf
```

## 1. CRM stack

```bash
cd /opt/repaircrm/crm
cp .env.production.example .env.production
# задать SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS, домены
docker compose --env-file .env.production -p repaircrm up -d --build
```

Compose стартует: `backend`, `frontend`, `db` (PostgreSQL 15), `redis`,
`celery-worker`, `celery-beat`, `subscription-checker`.

Создание суперпользователя:

```bash
DJANGO_SUPERUSER_USERNAME=admin \
DJANGO_SUPERUSER_EMAIL=admin@b00bs.ru \
DJANGO_SUPERUSER_PASSWORD='<strong_password>' \
docker compose -p repaircrm exec -T backend \
  python manage.py runscript init_superuser
```

## 2. Client Portal stack

```bash
cd /opt/repaircrm/client
cp .env.example .env.production
# задать SECRET_KEY, DB_URL, CORS_ORIGINS, SYNC_TOKEN
docker compose --env-file .env.production -p repaircrm-client up -d --build
```

## 3. Хостовый Nginx

```bash
cp /opt/repaircrm/crm/deploy/nginx/repaircrm-sites.conf \
   /etc/nginx/sites-available/repaircrm-sites.conf
ln -sf /etc/nginx/sites-available/repaircrm-sites.conf \
       /etc/nginx/sites-enabled/repaircrm-sites.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

Текущий конфиг обслуживает:

- `b00bs.ru` → `127.0.0.1:8080` (CRM frontend)
- `repire-status.ru`, `www.repire-status.ru` → `127.0.0.1:8081` (Client Portal)
- `client.b00bs.ru`, `portal.b00bs.ru` → `127.0.0.1:8081` (legacy aliases)

## 4. SSL / Let's Encrypt

### Установка Certbot

```bash
apt install -y certbot python3-certbot-nginx
```

### CRM домен

```bash
certbot --nginx \
  --non-interactive --agree-tos \
  --email admin@b00bs.ru \
  -d b00bs.ru -d www.b00bs.ru \
  --redirect
```

### Client Portal домен

```bash
certbot --nginx \
  --non-interactive --agree-tos \
  --email admin@b00bs.ru \
  -d repire-status.ru -d www.repire-status.ru \
  --redirect
```

> Перед запуском убедиться, что домен резолвится на IP сервера:
> ```bash
> dig +short repire-status.ru   # должен вернуть 130.49.151.251
> ```

Certbot автоматически:
- добавит `ssl_certificate` / `ssl_certificate_key` в nginx-блоки;
- вставит HTTP → HTTPS redirect;
- зарегистрирует systemd-timer для автопродления.

### Проверка автопродления

```bash
certbot renew --dry-run
systemctl status certbot.timer
```

### После получения TLS

В `.env.production` CRM включить:

```env
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://b00bs.ru,https://www.b00bs.ru
CORS_ALLOWED_ORIGINS=https://b00bs.ru,https://www.b00bs.ru
```

В `.env.production` Client Portal:

```env
CLIENT_PORTAL_CORS_ORIGINS=https://repire-status.ru,https://www.repire-status.ru
```

Перезапустить backend каждого стека:

```bash
docker compose -p repaircrm up -d --no-deps backend
docker compose -p repaircrm-client up -d --no-deps backend
```

## 5. Автозапуск (systemd)

```bash
# CRM
cat > /etc/systemd/system/repaircrm.service << 'EOF'
[Unit]
Description=Repair CRM
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/repaircrm/crm
ExecStart=docker compose --env-file .env.production -p repaircrm up -d
ExecStop=docker compose -p repaircrm down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

# Client Portal
cat > /etc/systemd/system/repaircrm-client.service << 'EOF'
[Unit]
Description=Repair CRM Client Portal
After=docker.service repaircrm.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/repaircrm/client
ExecStart=docker compose --env-file .env.production -p repaircrm-client up -d
ExecStop=docker compose -p repaircrm-client down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable repaircrm repaircrm-client
```

## 6. Обновление

```bash
# CRM
cd /opt/repaircrm/crm && git pull
docker compose --env-file .env.production -p repaircrm up -d --build

# Client Portal
cd /opt/repaircrm/client && git pull
docker compose --env-file .env.production -p repaircrm-client up -d --build
```

## 7. Резервные копии

### PostgreSQL

```bash
# CRM DB
docker compose -p repaircrm exec -T db \
  pg_dump -U postgres repair_crm | gzip > /backup/crm_$(date +%Y%m%d).sql.gz

# Client Portal DB
docker compose -p repaircrm-client exec -T db \
  pg_dump -U portal client_portal | gzip > /backup/client_$(date +%Y%m%d).sql.gz
```

### Media файлы (CRM)

```bash
docker run --rm \
  -v repaircrm_media:/data \
  -v /backup:/backup \
  alpine tar czf /backup/media_$(date +%Y%m%d).tar.gz -C /data .
```

### Автоматический крон

```bash
# /etc/cron.d/repaircrm-backup
0 3 * * * root \
  docker compose -p repaircrm exec -T db \
    pg_dump -U postgres repair_crm \
  | gzip > /backup/crm_$(date +\%Y\%m\%d).sql.gz
```

## 8. Мониторинг

```bash
# Статус
docker compose -p repaircrm ps
docker compose -p repaircrm-client ps

# Health checks
curl https://b00bs.ru/api/health
curl https://repire-status.ru/api/health

# Логи
docker compose -p repaircrm logs -f --tail=100 backend
docker compose -p repaircrm-client logs -f --tail=100 backend

# Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

## Диагностика

### Сайт не открывается

```bash
# Проверить контейнеры
docker compose -p repaircrm ps

# Проверить порт
curl -I http://127.0.0.1:8080/
curl -I http://127.0.0.1:8081/

# Проверить nginx
nginx -t
systemctl status nginx
```

### Certbot не выпускает сертификат

```bash
# Домен должен резолвиться на IP сервера
dig +short repire-status.ru

# 80 порт должен быть открыт
curl -I http://repire-status.ru/

# Повторный запуск с подробным логом
certbot --nginx -d repire-status.ru -d www.repire-status.ru -v
```

### Миграции не применились

```bash
docker compose -p repaircrm exec backend python manage.py showmigrations | grep '\[ \]'
docker compose -p repaircrm exec backend python manage.py migrate
```
