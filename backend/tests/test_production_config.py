from pathlib import Path

import yaml
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]


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

    def test_production_docs_include_subscription_scheduler(self):
        production_doc = (ROOT / "docs" / "PRODUCTION.md").read_text()

        self.assertIn("python manage.py check_subscriptions", production_doc)
