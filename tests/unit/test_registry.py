from typing import TYPE_CHECKING, Type

from django.core.files.storage import default_storage
from django.db import models
import pytest

if TYPE_CHECKING:
    # s3_file_field requires Django settings to be available at import time
    from s3_file_field.fields import S3FileField


# Declaring a Model has global side effects, so only do it once
@pytest.fixture(scope='session')
def s3ff_class(django_settings_init) -> Type[models.Model]:
    # s3_file_field requires Django settings to be available at import time
    from s3_file_field.fields import S3FileField

    class Resource(models.Model):
        class Meta:
            # Necessary since the class is defined outside of a real app
            app_label = 's3ff_test'

        blob = S3FileField()
        blob_2 = S3FileField()

    return Resource


@pytest.fixture
def s3ff_field(s3ff_class: Type[models.Model]) -> 'S3FileField':
    return s3ff_class._meta.get_field('blob')


def test_registry_get_field(s3ff_field: 'S3FileField'):
    # s3_file_field requires Django settings to be available at import time
    from s3_file_field._registry import get_field

    assert get_field(str(s3ff_field)) is s3ff_field


def test_registry_iter_fields(s3ff_field: 'S3FileField'):
    # s3_file_field requires Django settings to be available at import time
    from s3_file_field._registry import iter_fields

    fields = list(iter_fields())

    assert len(fields) == 2
    assert any(field is s3ff_field for field in fields)


def test_registry_iter_storages(s3ff_field: 'S3FileField'):
    # s3_file_field requires Django settings to be available at import time
    from s3_file_field._registry import iter_storages

    fields = list(iter_storages())

    assert len(fields) == 1
    assert fields[0] is default_storage
