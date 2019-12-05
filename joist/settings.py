import logging
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _s(key: str, default: Any = None):
    return getattr(settings, key, default)


def _guess_provider():
    storage = _s('DEFAULT_FILE_STORAGE')
    if storage == 'minio_storage.storage.MinioMediaStorage' or hasattr(
        settings, 'MINIO_STORAGE_MEDIA_BUCKET_NAME'
    ):
        return 'minio'
    if storage == 'storages.backends.s3boto3.S3Boto3Storage' or hasattr(
        settings, 'AWS_STORAGE_BUCKET_NAME'
    ):
        return 'aws'
    return 'unknown'


# configuration from django-storage for S3
AWS_ACCESS_KEY_ID = _s(
    'AWS_S3_ACCESS_KEY_ID', _s('AWS_ACCESS_KEY_ID', _s('MINIO_STORAGE_ACCESS_KEY'))
)
AWS_SECRET_ACCESS_KEY = _s(
    'AWS_S3_SECRET_ACCESS_KEY', _s('AWS_SECRET_ACCESS_KEY', _s('MINIO_STORAGE_SECRET_KEY'))
)
AWS_REGION = _s('AWS_S3_REGION_NAME', _s('AWS_REGION'))

AWS_S3_ENDPOINT_URL = _s('AWS_S3_ENDPOINT_URL', _s('MINIO_STORAGE_ENDPOINT'))
AWS_S3_USE_SSL = _s('AWS_S3_USE_SSL', _s('MINIO_STORAGE_USE_HTTPS'))

AWS_STORAGE_BUCKET_NAME = _s('AWS_STORAGE_BUCKET_NAME', _s('MINIO_STORAGE_MEDIA_BUCKET_NAME'))

JOIST_STORAGE_PROVIDER = _s('JOIST_STORAGE_PROVIDER', _guess_provider())

JOIST_UPLOAD_STS_ARN = _s('JOIST_UPLOAD_STS_ARN')
# in seconds 60 * 60 * 12 = 12h
JOIST_UPLOAD_DURATION = _s('JOIST_UPLOAD_DURATION', 60 * 60 * 12)
JOIST_API_BASE_URL = _s('JOIST_API_BASE_URL', '/api/joist')
JOIST_UPLOAD_PREFIX = _s('JOIST_UPLOAD_PREFIX', '')

# verify settings
if JOIST_STORAGE_PROVIDER == 'unknown':
    logging.getLogger('joist').warning(
        'joist is not configured properly, could not identify the storage provider (minio, aws), '
        'will fall back to default upload'
    )
elif any(v is None for v in [AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME]):
    raise ImproperlyConfigured(f'joist missing some required setting')
elif JOIST_STORAGE_PROVIDER == 'aws' and JOIST_UPLOAD_STS_ARN is None:
    raise ImproperlyConfigured(f'joist missing some JOIST_UPLOAD_STS_ARN setting')
elif JOIST_STORAGE_PROVIDER == 'minio' and AWS_S3_ENDPOINT_URL is None:
    raise ImproperlyConfigured(f'joist missing some AWS_S3_ENDPOINT_URL setting')
