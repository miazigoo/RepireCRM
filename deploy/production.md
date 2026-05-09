# Production deployment

This setup runs two Docker stacks behind the host Nginx:

- CRM: `127.0.0.1:8080`, default host `b00bs.ru`, IP fallback `192.168.0.97`
- Client portal: `127.0.0.1:8081`, hosts `client.b00bs.ru` and `portal.b00bs.ru`

Until DNS records are created, check the CRM by IP or with a Host header:

```bash
curl -I http://192.168.0.97/
curl -I -H 'Host: b00bs.ru' http://192.168.0.97/
curl -I -H 'Host: client.b00bs.ru' http://192.168.0.97/
```

## Server layout

```text
/opt/repaircrm/crm
/opt/repaircrm/client
/etc/nginx/sites-available/repaircrm-sites.conf
```

## CRM

```bash
cd /opt/repaircrm/crm
cp .env.production.example .env.production
# edit secrets before starting
docker compose --env-file .env.production -p repaircrm up -d --build
```

The CRM compose starts `backend`, `frontend`, `db`, `redis`, `subscription-checker`,
`celery-worker`, and `celery-beat`. Celery beat is required for scheduled portal
sync tasks.

## Client portal

```bash
cd /opt/repaircrm/client
cp .env.production.example .env.production
# use the same sync token and tenant key in the CRM integration settings
docker compose --env-file .env.production -p repaircrm-client up -d --build
```

## Host Nginx

```bash
cp /opt/repaircrm/crm/deploy/nginx/repaircrm-sites.conf /etc/nginx/sites-available/repaircrm-sites.conf
ln -sf /etc/nginx/sites-available/repaircrm-sites.conf /etc/nginx/sites-enabled/repaircrm-sites.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

After DNS is ready and TLS certificates are issued, switch the public URLs in both
`.env.production` files to HTTPS, set secure cookies to `True`, and enable HSTS.
