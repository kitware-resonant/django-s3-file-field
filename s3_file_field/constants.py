import enum
from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core.files.storage import Storage, default_storage


class StorageProvider(enum.Enum):
    AWS = enum.auto()
    MINIO = enum.auto()
    UNSUPPORTED = enum.auto()


def _get_storage_provider(storage: Storage = None) -> StorageProvider:
    if storage is None:
        storage = default_storage

    try:
        from storages.backends.s3boto3 import S3Boto3Storage

        if isinstance(storage, S3Boto3Storage):
            return StorageProvider.AWS
    except ImportError:
        pass

    try:
        from minio_storage.storage import MinioStorage

        if isinstance(storage, MinioStorage):
            return StorageProvider.MINIO
    except ImportError:
        pass

    return StorageProvider.UNSUPPORTED


def supported_storage(storage: Storage = None) -> bool:
    return _get_storage_provider(storage) != StorageProvider.UNSUPPORTED


# internal settings
S3FF_UPLOAD_DURATION = 60 * 60 * 12
# TODO move this here
S3FF_STORAGE_PROVIDER = _get_storage_provider()

# settings inferred from other packages (django-storages and django-minio-storage)
if S3FF_STORAGE_PROVIDER == StorageProvider.AWS:
    S3FF_ACCESS_KEY: Optional[str] = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    S3FF_SECRET_KEY: Optional[str] = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    S3FF_BUCKET: Optional[str] = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    S3FF_REGION: Optional[str] = getattr(settings, 'AWS_S3_REGION_NAME', None)
    # The boto3 client will default to using the standard AWS endpoint
    S3FF_ENDPOINT_URL: Optional[str] = None
    S3FF_PUBLIC_ENDPOINT_URL: Optional[str] = None

    S3FF_UPLOAD_STS_ARN: Optional[str] = getattr(settings, 'S3FF_UPLOAD_STS_ARN', None)
elif S3FF_STORAGE_PROVIDER == StorageProvider.MINIO:
    S3FF_ACCESS_KEY = getattr(settings, 'MINIO_STORAGE_ACCESS_KEY', None)
    S3FF_SECRET_KEY = getattr(settings, 'MINIO_STORAGE_SECRET_KEY', None)
    S3FF_BUCKET = getattr(settings, 'MINIO_STORAGE_MEDIA_BUCKET_NAME', None)
    # Boto needs some region to be set
    S3FF_REGION = 's3ff-minio-fake-region'

    # The boto3 client needs to know the Minio URL
    _use_ssl = getattr(settings, 'MINIO_STORAGE_USE_HTTPS', False)
    _endpoint = settings.MINIO_STORAGE_ENDPOINT
    S3FF_ENDPOINT_URL = f'http{"s" if _use_ssl else ""}://{_endpoint}'
    # End users may need access the store through a different URL, i.e. running Minio in docker
    _minio_storage_media_url = getattr(settings, 'MINIO_STORAGE_MEDIA_URL', None)
    if _minio_storage_media_url:
        # Try to parse the URL from MINIO_STORAGE_MEDIA_URL if it exists
        _url_parts = urlsplit(_minio_storage_media_url)
        S3FF_PUBLIC_ENDPOINT_URL = urlunsplit((_url_parts.scheme, _url_parts.netloc, '', '', ''))
    else:
        # Otherwise, default to using S3FF_ENDPOINT_URL
        S3FF_PUBLIC_ENDPOINT_URL = S3FF_ENDPOINT_URL

    # MinIO needs a valid ARN format, but the content doesn't matter
    # See https://github.com/minio/minio/blob/master/docs/sts/assume-role.md#testing
    S3FF_UPLOAD_STS_ARN = 'arn:s3ff:minio:fake:fake'
else:
    S3FF_ACCESS_KEY = None
    S3FF_SECRET_KEY = None
    S3FF_BUCKET = None
    S3FF_REGION = None

    S3FF_UPLOAD_STS_ARN = None


# user configurable settings
S3FF_UPLOAD_PREFIX = PurePosixPath(getattr(settings, 'S3FF_UPLOAD_PREFIX', ''))
