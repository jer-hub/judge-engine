"""Django settings for the competitive programming platform."""
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
    JWT_ACCESS_MINUTES=(int, 60),
    JWT_REFRESH_DAYS=(int, 7),
    JUDGE_DEFAULT_TIME_LIMIT_MS=(int, 2000),
    JUDGE_DEFAULT_MEMORY_LIMIT_MB=(int, 256),
    JUDGE_COMPILE_TIMEOUT_S=(int, 10),
    JUDGE_WALL_TIMEOUT_MULTIPLIER=(int, 3),
    JUDGE_SOURCE_MAX_BYTES=(int, 65536),
    JUDGE_STDIN_MAX_BYTES=(int, 16384),
    JUDGE_IMAGE=(str, "eclipse-temurin:17-jdk-jammy"),
    JUDGE_CONCURRENCY=(int, 4),
    SUBMISSION_THROTTLE_RATE=(str, "12/min"),
)

environ.Env.read_env(BASE_DIR.parent / ".env")

WEAK_SECRET_KEYS = frozenset(
    {
        "",
        "change-me-in-production",
        "insecure-dev-only-change-me",
        "dev-only-change-me-to-a-long-random-string-32b+",
        "dev-only-insecure-key-do-not-use-in-prod-32chars",
    }
)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env("DJANGO_DEBUG")

if not SECRET_KEY or SECRET_KEY in WEAK_SECRET_KEYS or len(SECRET_KEY) < 50:
    if DEBUG:
        SECRET_KEY = (
            "dev-only-insecure-key-do-not-use-in-prod-please-set-DJANGO_SECRET_KEY"
        )
        import logging

        logging.getLogger("django").warning(
            "Using insecure development DJANGO_SECRET_KEY. Set a strong secret before production."
        )
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set to a strong secret (length >= 50) when DEBUG is False."
        )

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "accounts",
    "problems",
    "contests",
    "submissions",
    "judge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="judge_engine"),
        "USER": env("POSTGRES_USER", default="judge"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="judge_dev_password"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

CORS_ALLOWED_ORIGINS = env("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "120/min",
        "submissions": env("SUBMISSION_THROTTLE_RATE"),
        "runs": "20/min",
        "login": "5/min",
        "logout": "10/min",
        "user-import": "6/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Judge configuration
JUDGE_DEFAULT_TIME_LIMIT_MS = env("JUDGE_DEFAULT_TIME_LIMIT_MS")
JUDGE_DEFAULT_MEMORY_LIMIT_MB = env("JUDGE_DEFAULT_MEMORY_LIMIT_MB")
JUDGE_COMPILE_TIMEOUT_S = env("JUDGE_COMPILE_TIMEOUT_S")
JUDGE_WALL_TIMEOUT_MULTIPLIER = env("JUDGE_WALL_TIMEOUT_MULTIPLIER")
JUDGE_SOURCE_MAX_BYTES = env("JUDGE_SOURCE_MAX_BYTES")
JUDGE_STDIN_MAX_BYTES = env("JUDGE_STDIN_MAX_BYTES")
JUDGE_IMAGE = env("JUDGE_IMAGE")
JUDGE_CONCURRENCY = env("JUDGE_CONCURRENCY")
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

DATA_UPLOAD_MAX_MEMORY_SIZE = (
    JUDGE_SOURCE_MAX_BYTES + JUDGE_STDIN_MAX_BYTES + 1024 * 64
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "judge": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
