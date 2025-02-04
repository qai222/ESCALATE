import os
from .base import *

DEBUG = 1
SECRET_KEY = "1qhmd^+6(k3t4$*^ws5px-f+loyi_%6@p)h33qha2z9wy6=*!4"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "escalate.sd2e.org", "[::1]"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "escalate",
        "USER": "escalate",
        "PASSWORD": "SD21sAwes0me3",
        "HOST": "escalate-postgres",
        "PORT": 5432,
        "OPTIONS": {
            #'options': '-c search_path=dev'
        },
    }
}

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        # 'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "url_filter.integrations.drf_coreapi.CoreAPIURLFilterBackend"
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    # 'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
}
