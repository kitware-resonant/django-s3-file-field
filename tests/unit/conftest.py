from typing import TYPE_CHECKING

from django.core.files.storage import Storage
from minio_storage.storage import MinioStorage
import pytest

if TYPE_CHECKING:
    # S3Boto3Storage requires Django settings to be available at import time
    from storages.backends.s3boto3 import S3Boto3Storage

from .storage import minio_storage_factory, s3boto3_storage_factory


def pytest_configure():
    # Make Django settings available for reading, without initializing Django apps
    from django.conf import settings

    settings.configure()


@pytest.fixture
def s3boto3_storage() -> 'S3Boto3Storage':
    return s3boto3_storage_factory()


@pytest.fixture
def minio_storage() -> MinioStorage:
    return minio_storage_factory()


@pytest.fixture(params=[s3boto3_storage_factory, minio_storage_factory], ids=['s3boto3', 'minio'])
def storage(request) -> Storage:
    storage_factory = request.param
    return storage_factory()
