import logging

from django.conf import settings

from .configuration import get_storage_provider


# internal settings
_JOIST_UPLOAD_DURATION = 60 * 60 * 12
_JOIST_STORAGE_PROVIDER = get_storage_provider()

# settings inferred from other packages (django-storages and django-minio-storage)
if _JOIST_STORAGE_PROVIDER == 'AWS':
    _JOIST_ACCESS_KEY = settings.AWS_ACCESS_KEY_ID
    _JOIST_SECRET_KEY = settings.AWS_SECRET_ACCESS_KEY
    _JOIST_BUCKET = settings.AWS_STORAGE_BUCKET_NAME
    _JOIST_REGION = getattr(settings, 'AWS_S3_REGION_NAME', None)
    _JOIST_ENDPOINT = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
    _JOIST_USE_SSL = getattr(settings, 'AWS_S3_USE_SSL', True)

    JOIST_UPLOAD_STS_ARN = settings.JOIST_UPLOAD_STS_ARN
elif _JOIST_STORAGE_PROVIDER == 'MINIO':
    _JOIST_ACCESS_KEY = settings.MINIO_STORAGE_ACCESS_KEY
    _JOIST_SECRET_KEY = settings.MINIO_STORAGE_SECRET_KEY
    _JOIST_BUCKET = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
    _JOIST_REGION = None
    _JOIST_ENDPOINT = settings.MINIO_STORAGE_ENDPOINT
    _JOIST_USE_SSL = settings.MINIO_STORAGE_USE_HTTPS

    # MinIO needs a valid ARN format, but the content doesn't matter
    # See https://github.com/minio/minio/blob/master/docs/sts/assume-role.md#testing
    JOIST_UPLOAD_STS_ARN = 'arn:xxx:xxx:xxx:xxxx'
else:
    # TODO: is this necessary since the check now runs this on runserver?
    logging.getLogger('joist').warning(
        'joist is not configured properly, could not identify the storage provider (minio, aws), '
        'will fall back to default upload'
    )


# user configurable settings
# TODO: make sure these work correctly regardless of leading/trailing slashes
JOIST_API_BASE_URL = getattr(settings, 'JOIST_API_BASE_URL', '/api/joist').rstrip('/')
JOIST_UPLOAD_PREFIX = getattr(settings, 'JOIST_UPLOAD_PREFIX', '')
