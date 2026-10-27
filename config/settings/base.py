"""Settings shared by every environment. Secrets come from the .env file."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SARTHI_VERSION = "0.1.0"

# ---- Core security ----
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# ---- Applications ----
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    # Sarthi core apps
    "apps.core",
    "apps.accounts",
    "apps.family",
    "apps.vault",
    "apps.wealth",
]

MIDDLEWARE = [
    "apps.core.middleware.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SarthiErrorMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.shell",
            ],
        },
    },
]

# ---- Database (SQLite for now) ----
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

# ---- Users ----
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---- Language and time ----
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ---- Static files ----
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Security hardening ----
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True

# ---- REST framework (kept minimal) ----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

# ---- Logging ----
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.core.logging_utils.RequestIdFilter"},
    },
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} [{request_id}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["request_id"],
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "sarthi.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "delay": True,
            "formatter": "standard",
            "filters": ["request_id"],
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "errors.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "delay": True,
            "level": "ERROR",
            "formatter": "standard",
            "filters": ["request_id"],
        },
    },
    "root": {
        "handlers": ["console", "app_file", "error_file"],
        "level": LOG_LEVEL,
    },
}


# ---- Phase 2: login pages, messages, backups ----
from django.contrib.messages import constants as message_constants

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
MESSAGE_TAGS = {message_constants.ERROR: "danger"}

BACKUP_DIR = BASE_DIR / "backups"
BACKUP_ENCRYPTION_KEY = env("BACKUP_ENCRYPTION_KEY", default="")
BACKUP_COPY_DIR = env("BACKUP_COPY_DIR", default="")
BACKUP_KEEP_AUTO = env.int("BACKUP_KEEP_AUTO", default=14)


# ---- Phase 3: private data (encryption, vault, sessions) ----
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")
FIELD_ENCRYPTION_OLD_KEYS = env.list("FIELD_ENCRYPTION_OLD_KEYS", default=[])
VAULT_DIR = BASE_DIR / "data" / "vault"
VAULT_MAX_UPLOAD_MB = env.int("VAULT_MAX_UPLOAD_MB", default=10)

# Sign out automatically after this many idle minutes
SESSION_IDLE_MINUTES = env.int("SESSION_IDLE_MINUTES", default=30)
SESSION_COOKIE_AGE = SESSION_IDLE_MINUTES * 60
SESSION_SAVE_EVERY_REQUEST = True

