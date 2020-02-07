import enum
import functools
import posixpath

from django.conf import settings
from django.urls import reverse
from django.utils.module_loading import import_string


class StorageProvider(enum.Enum):
    AWS = enum.auto()
    MINIO = enum.auto()
    UNSUPPORTED = enum.auto()


def get_storage_provider() -> StorageProvider:
    _storage_class = import_string(settings.DEFAULT_FILE_STORAGE)
    try:
        from storages.backends.s3boto3 import S3Boto3Storage

        if _storage_class == S3Boto3Storage or issubclass(_storage_class, S3Boto3Storage):
            return StorageProvider.AWS
    except ImportError:
        pass

    try:
        from minio_storage.storage import MinioMediaStorage

        if _storage_class == MinioMediaStorage or issubclass(_storage_class, MinioMediaStorage):
            return StorageProvider.MINIO
    except ImportError:
        pass

    return StorageProvider.UNSUPPORTED


@functools.lru_cache(maxsize=1)
def get_base_url() -> str:
    prepare_url = reverse('s3_file_field:upload-prepare')
    finalize_url = reverse('s3_file_field:upload-finalize')
    # Use posixpath to always parse URL paths with forward slashes
    return posixpath.commonpath([prepare_url, finalize_url])
