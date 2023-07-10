import django_heroku

from core.settings.base import *  # pylint: disable=unused-wildcard-import,wildcard-import

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

TIME_ZONE = "US/Pacific"

# Session settings
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "vendormanager",
        "USER": "mvp",
        "PASSWORD": "mvp",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"


django_heroku.settings(locals())
