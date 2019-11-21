from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _s(key: str, default: Any = None):
    return getattr(settings, key, default)


def _r(key: str):
    if not hasattr(settings, key):
        raise ImproperlyConfigured(f'joist requires the `{key}` setting')
    return getattr(settings, key)


# configuration from django-storage for S3
AWS_ACCESS_KEY_ID = _s('AWS_S3_SECRET_ACCESS_KEY', _s('AWS_SECRET_ACCESS_KEY'))
AWS_SECRET_ACCESS_KEY = _s('AWS_S3_ACCESS_KEY_ID', _s('AWS_ACCESS_KEY_ID'))
AWS_REGION = _s('AWS_S3_REGION_NAME', _s('AWS_REGION'))

AWS_STORAGE_BUCKET_NAME = _r('AWS_STORAGE_BUCKET_NAME')

JOIST_UPLOAD_STS_ARN = _r('JOIST_UPLOAD_STS_ARN')

# in seconds 60 * 60 * 12 = 12h
JOIST_UPLOAD_DURATION = _s('JOIST_UPLOAD_DURATION', 60 * 60 * 12)
JOIST_API_BASE_URL = _s('JOIST_API_BASE_URL', 'api/joist')
JOIST_UPLOAD_PREFIX = _s('JOIST_UPLOAD_PREFIX', '')
