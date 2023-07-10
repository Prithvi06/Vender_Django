# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import os

import dotenv
from decouple import config
from django.urls import reverse_lazy
from unipath import Path

dotenv.read_dotenv(override=True)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).parent.parent
CORE_DIR = Path(__file__).parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="S#perS3crEt_1122")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

# load production server from .env
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "*",
    config("SERVER", default="127.0.0.1"),
]

# Application definition

INSTALLED_APPS = [
    # local apps,
    "apps.authentication",
    "apps.home",
    "apps.vendor",
    "apps.administrator",
    "apps.incidents",
    "apps.tasks",
    "apps.utility",
    "apps.risks",
    "apps.notes",
    "apps.djf_surveys",
    "apps.equipments",
    "apps.systems",
    # other apps,
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "customselectwidget",
    "django_tables2",
    "organizations",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.microsoft",
    "allauth.socialaccount.providers.google",
]

SOCIALACCOUNT_PROVIDERS = {
    "microsoft": {
        "TENANT": "organizations",
    },
}

SOCIALACCOUNT_ADAPTER = "apps.authentication.gracen_socialaccount_adapter.GracenSocialAccountAdapter"
ACCOUNT_ADAPTER = "apps.authentication.gracen_account_adapter.GracenAccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
EMAIL_SUBJECT_PREFIX = ""

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_USER_MODEL = "authentication.User"
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.middleware.session_expired_middleware.SessionExpiredMiddleware",
    "apps.middleware.restrict_invite_user_middleware.RestrictInviteMemberMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]

ROOT_URLCONF = "core.urls"
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "account_login"
TEMPLATE_DIR = os.path.join(CORE_DIR, "apps/templates")  # ROOT dir for templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.djf_surveys.context_processors.surveys_context",
            ],
        },
    },
]


WSGI_APPLICATION = "core.wsgi.application"

# Database
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "gracen_poc",
        "USER": "mvp",
        "PASSWORD": "mvp",
        "HOST": "localhost"
    }
}
SITE_ID = 1
# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "US/Pacific"

USE_I18N = True

USE_L10N = True

USE_TZ = True

#############################################################
# SRC: https://devcenter.heroku.com/articles/django-assets

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(CORE_DIR, "staticfiles")
STATIC_URL = "/static/"

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (os.path.join(CORE_DIR, "apps/static"),)
#############################################################
#############################################################
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
AWS_QUERY_STRING_AUTH = bool(os.environ.get("AWS_QUERY_STRING_AUTH", "False"))
AWS_S3_FILE_OVERWRITE = bool(os.environ.get("AWS_S3_FILE_OVERWRITE", "False"))
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-west-1")

PHONENUMBER_DB_FORMAT = "NATIONAL"
PHONENUMBER_DEFAULT_REGION = "US"
PHONENUMBER_DEFAULT_FORMAT = "NATIONAL"

INVITATION_BACKEND = "apps.authentication.gracen_invitation_backend.GracenInvitationBackend"
INVITATION_SUCCESS_URL = reverse_lazy("vendors")

DEFAULT_FROM_EMAIL = "Gracen GRC <noreply@gracen.io>"

# Celery settings
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
if REDIS_URL.startswith("rediss:"):
    REDIS_URL = REDIS_URL + "?ssl_cert_reqs=CERT_NONE"
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_RESULT_SERIALIZER = "json"
CELERY_TAK_SERIALIZER = "json"

OFAC_SDN_CSV_URL = os.environ.get("OFAC_SDN_CSV_URL", "https://www.treasury.gov/ofac/downloads/sdn.csv")
OFAC_SDN_ALT_CSV_URL = os.environ.get("OFAC_SDN_ALT_CSV_URL", "https://www.treasury.gov/ofac/downloads/alt.csv")
OFAC_SDN_ADDRESS_CSV_URL = os.environ.get(
    "OFAC_SDN_ADDRESS_CSV_URL", "https://www.treasury.gov/ofac/downloads/add.csv"
)

# Session settings

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Email backend settings
EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
SENDGRID_API_KEY = "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"#os.environ.get("SENDGRID_API_KEY")
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_HOST_USER = "apikey"  # this is exactly the value 'apikey'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_PORT = 587
EMAIL_USE_TLS = True
FROM_EMAIL = os.environ.get("FROM_EMAIL", "Gracen GRC <noreply@gracen.io>")

SENDGRID_SANDBOX_MODE_IN_DEBUG = False

QUESTIONNAIRE_INVITATION_TTL = os.environ.get("QUESTIONNAIRE_INVITATION_TTL", "14")
