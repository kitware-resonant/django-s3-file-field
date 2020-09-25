from typing import Type, cast

from django.core.files.storage import FileSystemStorage, Storage
from django.db import models
import pytest

from s3_file_field.fields import S3FileField

from .storage import minio_storage_factory, s3boto3_storage_factory


def pytest_configure():
    # Make Django settings available for reading, without initializing Django apps
    from django.conf import settings

    settings.configure()


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

        blob_minio = S3FileField(storage=minio_storage_factory())
        blob_s3 = S3FileField(storage=s3boto3_storage_factory())
        blob_file = S3FileField(storage=FileSystemStorage())

    return Resource


@pytest.fixture(params=['blob_minio', 'blob_s3'], ids=['minio', 's3boto3'])
def s3ff_field(request, s3ff_class: Type[models.Model]) -> S3FileField:
    return cast(S3FileField, s3ff_class._meta.get_field(request.param))


@pytest.fixture
def s3ff_field_invalid(request, s3ff_class: Type[models.Model]) -> S3FileField:
    return cast(S3FileField, s3ff_class._meta.get_field('blob_file'))
