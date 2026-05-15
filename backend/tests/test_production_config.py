import json
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

    def test_frontend_uses_local_material_icon_font(self):
        index_html = (ROOT / "frontend" / "crm-app" / "src" / "index.html").read_text()
        styles_css = (ROOT / "frontend" / "crm-app" / "src" / "styles.css").read_text()
        font_path = (
            ROOT
            / "frontend"
            / "crm-app"
            / "src"
            / "assets"
            / "fonts"
            / "MaterialIcons-Regular.ttf"
        )

        self.assertNotIn("fonts.googleapis.com/icon", index_html)
        self.assertIn("/assets/fonts/MaterialIcons-Regular.ttf", styles_css)
        self.assertTrue(font_path.exists())

    def test_frontend_production_build_keeps_stylesheet_csp_compatible(self):
        angular_config = json.loads(
            (ROOT / "frontend" / "crm-app" / "angular.json").read_text()
        )
        optimization = angular_config["projects"]["crm-app"]["architect"]["build"][
            "options"
        ]["optimization"]

        self.assertFalse(optimization["fonts"])
        self.assertTrue(optimization["scripts"])
        self.assertTrue(optimization["styles"]["minify"])
        self.assertFalse(optimization["styles"]["inlineCritical"])

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
        self.assertIn("SECURE_HSTS_INCLUDE_SUBDOMAINS=False", env_template)
        self.assertIn("SECURE_HSTS_PRELOAD=False", env_template)
        self.assertIn("SUBSCRIPTION_CHECK_INTERVAL_SECONDS=86400", env_template)
        self.assertIn("POSTGRES_BACKUP_INTERVAL_SECONDS=86400", env_template)
        self.assertIn("POSTGRES_BACKUP_RETENTION_DAYS=14", env_template)
        self.assertIn("BACKUP_INCLUDE_MEDIA=true", env_template)
        self.assertIn("BACKUP_RCLONE_REMOTE=", env_template)
        self.assertIn("MONITOR_TARGETS=", env_template)
        self.assertIn("ALERT_WEBHOOK_URL=", env_template)
        self.assertIn("SENTRY_DSN=", env_template)
        self.assertIn("EMAIL_HOST=", env_template)
        self.assertIn("COMMUNICATIONS_ENABLE_EMAIL=false", env_template)
        self.assertIn("COMMUNICATIONS_ENABLE_SMS=false", env_template)

    def test_backend_environment_exposes_production_integrations(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        environment = compose["x-backend-environment"]

        self.assertIn("SENTRY_DSN", environment)
        self.assertIn("SENTRY_TRACES_SAMPLE_RATE", environment)
        self.assertIn("SENTRY_SEND_DEFAULT_PII", environment)
        self.assertIn("EMAIL_HOST", environment)
        self.assertIn("COMMUNICATIONS_ENABLE_EMAIL", environment)
        self.assertIn("COMMUNICATIONS_ENABLE_SMS", environment)
        self.assertIn("TWILIO_ACCOUNT_SID", environment)

    def test_production_docs_include_subscription_scheduler(self):
        production_doc = (ROOT / "docs" / "PRODUCTION.md").read_text()

        self.assertIn("subscription-checker", production_doc)
        self.assertIn("python manage.py check_subscriptions", production_doc)
        self.assertIn("db-backup", production_doc)
        self.assertIn("pg_dump", production_doc)
        self.assertIn("BACKUP_RCLONE_REMOTE", production_doc)
        self.assertIn("health-monitor", production_doc)
        self.assertIn("ALERT_WEBHOOK_URL", production_doc)

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
        backup_script = (ROOT / "docker" / "backup-loop.sh").read_text()

        self.assertEqual(service["build"]["dockerfile"], "docker/Dockerfile.backup")
        self.assertIn("pg_dump", backup_script)
        self.assertIn("rclone copy", backup_script)
        self.assertEqual(
            service["environment"]["POSTGRES_BACKUP_INTERVAL_SECONDS"],
            "${POSTGRES_BACKUP_INTERVAL_SECONDS:-86400}",
        )
        self.assertEqual(
            service["environment"]["POSTGRES_BACKUP_RETENTION_DAYS"],
            "${POSTGRES_BACKUP_RETENTION_DAYS:-14}",
        )
        self.assertEqual(
            service["environment"]["BACKUP_INCLUDE_MEDIA"],
            "${BACKUP_INCLUDE_MEDIA:-true}",
        )
        self.assertIn("BACKUP_RCLONE_REMOTE", service["environment"])
        self.assertIn("RCLONE_CONFIG_B64", service["environment"])
        self.assertIn("ALERT_WEBHOOK_URL", service["environment"])
        self.assertEqual(service["depends_on"]["db"]["condition"], "service_healthy")
        self.assertIn("backup_data:/backups", service["volumes"])
        self.assertIn("media_data:/media:ro", service["volumes"])
        self.assertIn("backup_data", compose["volumes"])

    def test_production_compose_runs_health_monitor(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        service = compose["services"]["health-monitor"]
        monitor_script = (ROOT / "docker" / "health-monitor.sh").read_text()

        self.assertEqual(service["build"]["dockerfile"], "docker/Dockerfile.monitor")
        self.assertIn("MONITOR_TARGETS", monitor_script)
        self.assertIn("curl -fsS", monitor_script)
        self.assertIn("ALERT_WEBHOOK_URL", service["environment"])
        self.assertEqual(
            service["environment"]["MONITOR_FAILURE_THRESHOLD"],
            "${MONITOR_FAILURE_THRESHOLD:-3}",
        )
        self.assertEqual(
            service["depends_on"]["frontend"]["condition"], "service_healthy"
        )
        self.assertEqual(
            service["depends_on"]["backend"]["condition"], "service_healthy"
        )
