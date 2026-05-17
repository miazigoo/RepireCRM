import os
from pathlib import Path

import dj_database_url
import sentry_sdk
from corsheaders.defaults import default_headers
from decouple import config
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = config("ENVIRONMENT", default="development")
DEBUG = config("DEBUG", default=False, cast=bool)
_SECRET_KEY = config("SECRET_KEY", default="")

if ENVIRONMENT == "production" and not _SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required when ENVIRONMENT=production")

SECRET_KEY = _SECRET_KEY or "insecure-development-only-key-for-local-tests"

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,backend,127.0.0.1,0.0.0.0,testserver"
).split(",")

# Мультифилиальность
SHOP_MODEL = "shops.Shop"
USER_SHOP_FIELD = "shop"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "corsheaders",
    "phonenumber_field",
    "sequences",
    # Local apps
    "customers",
    "orders",
    "device",
    "inventory",
    "documents",
    "shops",  # приложение для магазинов
    "users",  # Кастомная модель пользователя
    "finance",  # Для финансов и оплат
    "loyalty",
    "notifications",
    "reports",
    "tasks",
    "analytics",
    "client_sync",
    "promotions",
    "data_import.apps.DataImportConfig",
    "admin_agent.apps.AdminAgentConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.RequestIdMiddleware",  # Attach X-Request-Id for tracing
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ShopMiddleware",  # Кастомный middleware для магазинов
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",  # Путь к кастомным шаблонам (опционально)
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Database - обновленная конфигурация
DATABASE_URL = config("DATABASE_URL", default=None)

if DATABASE_URL:
    # Используем DATABASE_URL если он задан (для Docker)
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    # Используем отдельные параметры для локальной разработки
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB", default="repair_crm"),
            "USER": config("POSTGRES_USER", default="postgres"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="postgres"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

# Redis
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# CORS settings
_default_cors = "http://localhost:4200,http://127.0.0.1:4200"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in config("CORS_ALLOWED_ORIGINS", default=_default_cors).split(",")
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-current-shop",
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in config("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)
SESSION_COOKIE_SECURE = config(
    "SESSION_COOKIE_SECURE",
    default=not DEBUG and ENVIRONMENT == "production",
    cast=bool,
)
CSRF_COOKIE_SECURE = config(
    "CSRF_COOKIE_SECURE", default=not DEBUG and ENVIRONMENT == "production", cast=bool
)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Public URLs used in payment redirects. In production set both to HTTPS domains.
FRONTEND_URL = config("FRONTEND_URL", default="http://127.0.0.1:4200")
BACKEND_PUBLIC_URL = config("BACKEND_PUBLIC_URL", default="http://127.0.0.1:8030")

# YooKassa/Yandex Kassa credentials. Local development defaults to a mock
# checkout page so payments can be tested without real secrets.
YOOKASSA_SHOP_ID = config("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = config("YOOKASSA_SECRET_KEY", default="")
YOOKASSA_API_URL = config("YOOKASSA_API_URL", default="https://api.yookassa.ru/v3")
_yookassa_default_mock = "false" if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY else "true"
YOOKASSA_MOCK = config("YOOKASSA_MOCK", default=_yookassa_default_mock, cast=bool)
YOOKASSA_CAPTURE = config("YOOKASSA_CAPTURE", default=True, cast=bool)

# Custom user model
AUTH_USER_MODEL = "users.User"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "json": {
            "format": (
                '{"level": "%(levelname)s", "time": "%(asctime)s", '
                '"module": "%(module)s", "message": "%(message)s"}'
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "repair_crm.log"),
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "repair_crm": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
os.makedirs(BASE_DIR / "logs", exist_ok=True)


SENTRY_DSN = config("SENTRY_DSN", default=None)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.0, cast=float),
        send_default_pii=config("SENTRY_SEND_DEFAULT_PII", default=False, cast=bool),
        environment=ENVIRONMENT,
    )


# Email
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=25, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@repair-crm.local")

# Коммуникации
COMMUNICATIONS_ENABLE_EMAIL = config(
    "COMMUNICATIONS_ENABLE_EMAIL", default=True, cast=bool
)
COMMUNICATIONS_ENABLE_SMS = config(
    "COMMUNICATIONS_ENABLE_SMS", default=False, cast=bool
)

# Twilio (опционально)
TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default=None)
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default=None)
TWILIO_FROM_NUMBER = config("TWILIO_FROM_NUMBER", default=None)

# Клиентский кабинет
PORTAL_DEFAULT_SHOP_CODE = config("PORTAL_DEFAULT_SHOP_CODE", default="")

# Центральная RepireCRM Admin. Используется только для коммерческого контура:
# подписка, промо-кампании, support, агрегированный heartbeat VPS.
ADMIN_SERVICE_URL = config("ADMIN_SERVICE_URL", default="")
ADMIN_SERVICE_AGENT_TOKEN = config("ADMIN_SERVICE_AGENT_TOKEN", default="")
ADMIN_SERVICE_HEARTBEAT_ENABLED = config(
    "ADMIN_SERVICE_HEARTBEAT_ENABLED", default=False, cast=bool
)
ADMIN_SERVICE_HEARTBEAT_INTERVAL_SECONDS = config(
    "ADMIN_SERVICE_HEARTBEAT_INTERVAL_SECONDS", default=300, cast=int
)
ADMIN_SERVICE_TIMEOUT_SECONDS = config(
    "ADMIN_SERVICE_TIMEOUT_SECONDS", default=5, cast=int
)
ADMIN_SERVICE_ENFORCEMENT_ENABLED = config(
    "ADMIN_SERVICE_ENFORCEMENT_ENABLED", default=False, cast=bool
)
ADMIN_SERVICE_ENFORCEMENT_REQUIRE_SYNC = config(
    "ADMIN_SERVICE_ENFORCEMENT_REQUIRE_SYNC", default=False, cast=bool
)
ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS = config(
    "ADMIN_SERVICE_ENFORCEMENT_STALE_GRACE_HOURS", default=72, cast=int
)
ADMIN_SERVICE_ENFORCEMENT_ALLOW_SUPERUSER_BYPASS = config(
    "ADMIN_SERVICE_ENFORCEMENT_ALLOW_SUPERUSER_BYPASS", default=True, cast=bool
)
APP_VERSION = config("APP_VERSION", default="")


CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TIMEZONE = config("CELERY_TIMEZONE", default="Europe/Moscow")

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "low-stock-scan-daily": {
        "task": "tasks.tasks.low_stock_scan",
        "schedule": crontab(hour=3, minute=0),  # 03:00 every day
    },
    "expire-loyalty-points-daily": {
        "task": "loyalty.tasks.expire_points",
        "schedule": crontab(hour=3, minute=30),  # 03:30 every day
    },
    "analytics-monthly-snapshot": {
        "task": "analytics.tasks.save_monthly_snapshots",
        "schedule": crontab(hour=4, minute=0),  # 04:00 every day
    },
    "client-sync-portals-every-minute": {
        "task": "client_sync.tasks.sync_client_portals",
        "schedule": 60,  # every 60 seconds
    },
}

if ADMIN_SERVICE_HEARTBEAT_ENABLED:
    CELERY_BEAT_SCHEDULE["admin-agent-heartbeat"] = {
        "task": "admin_agent.tasks.send_admin_heartbeat",
        "schedule": ADMIN_SERVICE_HEARTBEAT_INTERVAL_SECONDS,
    }
