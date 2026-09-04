import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEPLOYMENT_ENV = os.environ.get("DJANGO_ENV", "development").strip().lower()
PRODUCTION = DEPLOYMENT_ENV == "production"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-local-development-only")
if PRODUCTION:
    if (
        not os.environ.get("DJANGO_SECRET_KEY")
        or len(SECRET_KEY) < 50
        or len(set(SECRET_KEY)) < 5
        or SECRET_KEY.startswith("django-insecure-")
    ):
        raise RuntimeError("DJANGO_SECRET_KEY must be a long, random value in production")


def _env_flag(name, default):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = _env_flag("DJANGO_DEBUG", False if PRODUCTION else True)
SECURE_DEFAULT = PRODUCTION
SECURE_SSL_REDIRECT = _env_flag("DJANGO_SECURE_SSL_REDIRECT", SECURE_DEFAULT)
SESSION_COOKIE_SECURE = _env_flag("DJANGO_SESSION_COOKIE_SECURE", SECURE_DEFAULT)
CSRF_COOKIE_SECURE = _env_flag("DJANGO_CSRF_COOKIE_SECURE", SECURE_DEFAULT)
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000" if PRODUCTION else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_flag("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", PRODUCTION)
SECURE_HSTS_PRELOAD = _env_flag("DJANGO_SECURE_HSTS_PRELOAD", PRODUCTION)
if PRODUCTION and (DEBUG or not SECURE_SSL_REDIRECT or not SESSION_COOKIE_SECURE or not CSRF_COOKIE_SECURE):
    raise RuntimeError("Production security settings cannot be weakened")
if PRODUCTION and (SECURE_HSTS_SECONDS < 31536000 or not SECURE_HSTS_INCLUDE_SUBDOMAINS or not SECURE_HSTS_PRELOAD):
    raise RuntimeError("Production HSTS settings must be enabled for at least one year")
DEFAULT_ALLOWED_HOSTS = "localhost,127.0.0.1,0.0.0.0,testserver"
if PRODUCTION and not os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip():
    raise RuntimeError("DJANGO_ALLOWED_HOSTS is required in production")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).split(",")
    if host.strip()
]

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
DEMO_LOGIN_ENABLED = os.environ.get("DEMO_LOGIN_ENABLED", "False").lower() in {"1", "true", "yes", "on"}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "pharmacy.apps.PharmacyConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "lakasahara.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pharmacy.context_processors.notifications",
            ]
        },
    }
]
WSGI_APPLICATION = "lakasahara.wsgi.application"
DB_ENGINE = os.environ.get("DB_ENGINE", "sqlite3").strip().lower()
if DB_ENGINE in {"postgres", "postgresql"}:
    DB_ENGINE = "django.db.backends.postgresql"
elif DB_ENGINE in {"sqlite", "sqlite3"}:
    DB_ENGINE = "django.db.backends.sqlite3"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3").strip().lower()
        if os.environ.get("DB_ENGINE")
        else "django.db.backends.sqlite3",
        "NAME": os.environ.get("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}
DATABASES["default"]["ENGINE"] = DB_ENGINE
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
LOGIN_URL = "/login/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
