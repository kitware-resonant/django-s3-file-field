from typing import TYPE_CHECKING

import django
from django.core.files.storage import Storage
from minio_storage.storage import MinioStorage
import pytest

if TYPE_CHECKING:
    # S3Boto3Storage requires Django settings to be available at import time
    from storages.backends.s3boto3 import S3Boto3Storage

from .storage import minio_storage_factory, s3boto3_storage_factory


# Session scope, as execution has global state side effects
@pytest.fixture(scope='session')
def django_settings_init() -> None:
    """Make Django settings available for reading, without initializing Django apps."""
    from django.conf import settings

    settings.configure()
    django.setup()


@pytest.fixture
def s3boto3_storage(django_settings_init) -> 'S3Boto3Storage':
    return s3boto3_storage_factory()


@pytest.fixture
def minio_storage(django_settings_init) -> MinioStorage:
    return minio_storage_factory()


@pytest.fixture(params=[s3boto3_storage_factory, minio_storage_factory], ids=['s3boto3', 'minio'])
def storage(request, django_settings_init) -> Storage:
    storage_factory = request.param
    return storage_factory()
