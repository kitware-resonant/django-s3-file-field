import logging

from django.conf import settings
from django.utils.module_loading import import_string


# internal settings
_JOIST_UPLOAD_DURATION = 60 * 60 * 12
_JOIST_STORAGE_PROVIDER = None

_storage_class = import_string(settings.DEFAULT_FILE_STORAGE)
try:
    from storages.backends.s3boto3 import S3Boto3Storage

    if _storage_class == S3Boto3Storage or issubclass(_storage_class, S3Boto3Storage):
        _JOIST_STORAGE_PROVIDER = 'AWS'
except ImportError:
    pass

try:
    from minio_storage.storage import MinioMediaStorage

    if _storage_class == MinioMediaStorage or issubclass(_storage_class, MinioMediaStorage):
        _JOIST_STORAGE_PROVIDER = 'MINIO'
except ImportError:
    pass

# settings inferred from other packages (django-storages and django-minio-storage)
if _JOIST_STORAGE_PROVIDER == 'AWS':
    _JOIST_ACCESS_KEY = settings.AWS_ACCESS_KEY_ID
    _JOIST_SECRET_KEY = settings.AWS_SECRET_ACCESS_KEY
    _JOIST_BUCKET = settings.AWS_STORAGE_BUCKET_NAME
    _JOIST_REGION = getattr(settings, 'AWS_S3_REGION_NAME', None)
    _JOIST_ENDPOINT = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
    _JOIST_USE_SSL = getattr(settings, 'AWS_S3_USE_SSL', True)
elif _JOIST_STORAGE_PROVIDER == 'MINIO':
    _JOIST_ACCESS_KEY = settings.MINIO_STORAGE_ACCESS_KEY
    _JOIST_SECRET_KEY = settings.MINIO_STORAGE_SECRET_KEY
    _JOIST_BUCKET = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
    _JOIST_REGION = None
    _JOIST_ENDPOINT = settings.MINIO_STORAGE_ENDPOINT
    _JOIST_USE_SSL = settings.MINIO_STORAGE_USE_HTTPS
else:
    logging.getLogger('joist').warning(
        'joist is not configured properly, could not identify the storage provider (minio, aws), '
        'will fall back to default upload'
    )


# user configurable settings
JOIST_UPLOAD_STS_ARN = settings.JOIST_UPLOAD_STS_ARN

# TODO: make sure these work correctly regardless of leading/trailing slashes
JOIST_API_BASE_URL = getattr(settings, 'JOIST_API_BASE_URL', '/api/joist').rstrip('/')
JOIST_UPLOAD_PREFIX = getattr(settings, 'JOIST_UPLOAD_PREFIX', '')
