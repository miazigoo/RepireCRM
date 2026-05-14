import os
from pathlib import Path

import yaml
from django.test import SimpleTestCase

ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))


class ProductionConfigTestCase(SimpleTestCase):
    def test_production_compose_references_existing_dockerfiles(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())

        for service in compose["services"].values():
            build = service.get("build")
            if not build:
                continue
            dockerfile = ROOT / build["dockerfile"]
            self.assertTrue(
                dockerfile.exists(),
                f"Missing Dockerfile referenced by compose: {dockerfile}",
            )

    def test_frontend_nginx_preserves_api_prefix(self):
        nginx_conf = (ROOT / "docker" / "nginx.conf").read_text()

        self.assertIn("location /api/", nginx_conf)
        self.assertIn("proxy_pass http://backend:8000;", nginx_conf)
        self.assertNotIn("proxy_pass http://backend:8000/;", nginx_conf)

    def test_frontend_nginx_keeps_security_headers_in_cached_locations(self):
        nginx_conf = (ROOT / "docker" / "nginx.conf").read_text()
        headers_conf = (ROOT / "docker" / "security-headers.conf").read_text()

        self.assertIn("Content-Security-Policy", headers_conf)
        self.assertIn("frame-ancestors 'none'", headers_conf)
        self.assertIn("location ~* ", nginx_conf)
        self.assertIn(
            'Cache-Control "public, max-age=2592000, immutable" always',
            nginx_conf,
        )
        self.assertIn('Cache-Control "public, max-age=604800" always', nginx_conf)
        self.assertGreaterEqual(
            nginx_conf.count("include /etc/nginx/snippets/security-headers.conf;"),
            4,
        )

    def test_frontend_nginx_serves_local_icon_fonts_with_correct_mime_types(self):
        nginx_conf = (ROOT / "docker" / "nginx.conf").read_text()

        self.assertIn(r"location ~* \.(?:woff2?|ttf|otf|eot)$", nginx_conf)
        self.assertIn("font/otf otf;", nginx_conf)
        self.assertIn("font/woff2 woff2;", nginx_conf)
        self.assertIn(
            "X-Content-Type-Options",
            (ROOT / "docker" / "security-headers.conf").read_text(),
        )

    def test_backend_container_uses_gunicorn_entrypoint(self):
        dockerfile = (ROOT / "docker" / "Dockerfile.backend").read_text()
        entrypoint = (ROOT / "docker" / "backend-entrypoint.sh").read_text()

        self.assertIn('CMD ["/entrypoint.sh"]', dockerfile)
        self.assertIn("gunicorn core.wsgi:application", entrypoint)
        self.assertIn("python manage.py migrate --noinput", entrypoint)
        self.assertIn("python manage.py collectstatic --noinput", entrypoint)

    def test_production_env_template_requires_critical_secrets(self):
        env_template = (ROOT / ".env.production.example").read_text()

        self.assertIn("SECRET_KEY=", env_template)
        self.assertIn("POSTGRES_PASSWORD=", env_template)
        self.assertIn("ALLOWED_HOSTS=", env_template)
        self.assertIn("127.0.0.1", env_template)
        self.assertIn("CSRF_TRUSTED_ORIGINS=", env_template)
        self.assertIn("SUBSCRIPTION_CHECK_INTERVAL_SECONDS=86400", env_template)
        self.assertIn("POSTGRES_BACKUP_INTERVAL_SECONDS=86400", env_template)
        self.assertIn("POSTGRES_BACKUP_RETENTION_DAYS=14", env_template)

    def test_production_docs_include_subscription_scheduler(self):
        production_doc = (ROOT / "docs" / "PRODUCTION.md").read_text()

        self.assertIn("subscription-checker", production_doc)
        self.assertIn("python manage.py check_subscriptions", production_doc)
        self.assertIn("db-backup", production_doc)
        self.assertIn("pg_dump", production_doc)

    def test_frontend_service_has_healthcheck(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        frontend = compose["services"]["frontend"]

        self.assertIn("healthcheck", frontend)
        self.assertIn("http://127.0.0.1/", frontend["healthcheck"]["test"][1])

    def test_production_compose_runs_subscription_scheduler(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        service = compose["services"]["subscription-checker"]

        self.assertIn("python manage.py check_subscriptions", service["command"])
        self.assertEqual(
            service["environment"]["SUBSCRIPTION_CHECK_INTERVAL_SECONDS"],
            "${SUBSCRIPTION_CHECK_INTERVAL_SECONDS:-86400}",
        )
        self.assertEqual(
            service["depends_on"]["backend"]["condition"], "service_healthy"
        )

    def test_production_compose_runs_database_backups(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        service = compose["services"]["db-backup"]

        self.assertEqual(service["image"], "postgres:15-alpine")
        self.assertIn("pg_dump", service["command"])
        self.assertEqual(
            service["environment"]["POSTGRES_BACKUP_INTERVAL_SECONDS"],
            "${POSTGRES_BACKUP_INTERVAL_SECONDS:-86400}",
        )
        self.assertEqual(
            service["environment"]["POSTGRES_BACKUP_RETENTION_DAYS"],
            "${POSTGRES_BACKUP_RETENTION_DAYS:-14}",
        )
        self.assertEqual(service["depends_on"]["db"]["condition"], "service_healthy")
        self.assertIn("backup_data:/backups", service["volumes"])
        self.assertIn("backup_data", compose["volumes"])
