import os

from .base import *

ALLOWED_HOSTS += (os.environ.get("HEROKU_APP_NAME"),)
SITE_ID = int(os.environ.get("SITE_ID", "1"))
