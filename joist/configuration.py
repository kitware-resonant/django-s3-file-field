from django.conf import settings
from django.utils.module_loading import import_string


def get_storage_provider():
    provider = None

    _storage_class = import_string(settings.DEFAULT_FILE_STORAGE)
    try:
        from storages.backends.s3boto3 import S3Boto3Storage

        if _storage_class == S3Boto3Storage or issubclass(_storage_class, S3Boto3Storage):
            provider = 'AWS'
    except ImportError:
        pass

    try:
        from minio_storage.storage import MinioMediaStorage

        if _storage_class == MinioMediaStorage or issubclass(_storage_class, MinioMediaStorage):
            provider = 'MINIO'
    except ImportError:
        pass

    return provider
