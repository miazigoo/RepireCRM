import os
from pathlib import Path

import dj_database_url
import sentry_sdk
from decouple import config
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="your-secret-key-here")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,backend,127.0.0.1,0.0.0.0"
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
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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
    "django.contrib.auth.hashers.BCryptSHA256Hasher",
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

CORS_ALLOW_CREDENTIALS = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

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
            "format": '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/repair_crm.log",
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
os.makedirs("logs", exist_ok=True)


SENTRY_DSN = config("SENTRY_DSN", default=None)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.0, cast=float),
        send_default_pii=True,
        environment=config("ENVIRONMENT", default="development"),
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


CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TIMEZONE = config("CELERY_TIMEZONE", default="Europe/Moscow")
CELERY_BEAT_SCHEDULE = {
    "low-stock-scan-daily": {
        "task": "tasks.tasks.low_stock_scan",
        "schedule": 60 * 60 * 24,  # раз в сутки
    },
    "expire-loyalty-points-daily": {
        "task": "loyalty.tasks.expire_points",
        "schedule": 60 * 60 * 24,
    },
    "analytics-monthly-snapshot": {
        "task": "analytics.tasks.save_monthly_snapshots",
        "schedule": 60 * 60 * 24,  # раз в сутки
    },
}
