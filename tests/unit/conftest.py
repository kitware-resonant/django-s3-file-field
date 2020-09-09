from typing import TYPE_CHECKING, Type, cast

from django.core.files.storage import Storage
from django.db import models
from minio_storage.storage import MinioStorage
import pytest

if TYPE_CHECKING:
    # S3Boto3Storage requires Django settings to be available at import time
    from storages.backends.s3boto3 import S3Boto3Storage

from s3_file_field.fields import S3FileField

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


# Declaring a Model has global side effects, so only do it once
@pytest.fixture(scope='session')
def s3ff_class() -> Type[models.Model]:
    class Resource(models.Model):
        class Meta:
            # Necessary since the class is defined outside of a real app
            app_label = 's3ff_test'

        blob = S3FileField()
        blob_2 = S3FileField()

    return Resource


@pytest.fixture
def s3ff_field(s3ff_class: Type[models.Model]) -> S3FileField:
    return cast(S3FileField, s3ff_class._meta.get_field('blob'))
