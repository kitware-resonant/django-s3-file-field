from pathlib import PurePosixPath
from typing import Optional

from django.conf import settings

from .configuration import get_storage_provider, StorageProvider


# internal settings
_S3FF_UPLOAD_DURATION = 60 * 60 * 12
_S3FF_STORAGE_PROVIDER = get_storage_provider()

# settings inferred from other packages (django-storages and django-minio-storage)
if _S3FF_STORAGE_PROVIDER == StorageProvider.AWS:
    _S3FF_ACCESS_KEY: Optional[str] = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    _S3FF_SECRET_KEY: Optional[str] = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    _S3FF_BUCKET: Optional[str] = settings.AWS_STORAGE_BUCKET_NAME
    _S3FF_REGION: Optional[str] = getattr(settings, 'AWS_S3_REGION_NAME', None)
    _S3FF_ENDPOINT: Optional[str] = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
    _S3FF_USE_SSL: Optional[str] = getattr(settings, 'AWS_S3_USE_SSL', True)

    S3FF_UPLOAD_STS_ARN: Optional[str] = settings.S3FF_UPLOAD_STS_ARN
elif _S3FF_STORAGE_PROVIDER == StorageProvider.MINIO:
    _S3FF_ACCESS_KEY = settings.MINIO_STORAGE_ACCESS_KEY
    _S3FF_SECRET_KEY = settings.MINIO_STORAGE_SECRET_KEY
    _S3FF_BUCKET = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
    # Boto needs some region to be set
    _S3FF_REGION = 's3ff-minio-fake-region'
    _S3FF_ENDPOINT = settings.MINIO_STORAGE_ENDPOINT
    _S3FF_USE_SSL = settings.MINIO_STORAGE_USE_HTTPS

    # MinIO needs a valid ARN format, but the content doesn't matter
    # See https://github.com/minio/minio/blob/master/docs/sts/assume-role.md#testing
    S3FF_UPLOAD_STS_ARN = 'arn:s3ff:minio:fake:fake'
else:
    _S3FF_ACCESS_KEY = None
    _S3FF_SECRET_KEY = None
    _S3FF_BUCKET = None
    _S3FF_REGION = None
    _S3FF_ENDPOINT = None
    _S3FF_USE_SSL = None

    S3FF_UPLOAD_STS_ARN = None


# user configurable settings
S3FF_UPLOAD_PREFIX = PurePosixPath(getattr(settings, 'S3FF_UPLOAD_PREFIX', ''))
