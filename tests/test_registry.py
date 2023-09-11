from typing import cast

from django.core.files.storage import default_storage
import pytest

from s3_file_field import _registry
from s3_file_field.fields import S3FileField
from test_app.models import Resource


@pytest.fixture
def s3ff_field() -> S3FileField:
    """Return an attached S3FileField (not S3FieldFile) instance."""
    return cast(S3FileField, Resource._meta.get_field("blob"))


def test_field_id(s3ff_field: S3FileField):
    assert s3ff_field.id == "test_app.Resource.blob"


def test_field_id_premature():
    s3ff_field = S3FileField()
    with pytest.raises(Exception, match=r"contribute_to_class"):
        s3ff_field.id


def test_registry_get_field(s3ff_field: S3FileField):
    assert _registry.get_field(s3ff_field.id) is s3ff_field


def test_registry_iter_fields(s3ff_field: S3FileField):
    fields = list(_registry.iter_fields())

    assert len(fields) == 3
    assert any(field is s3ff_field for field in fields)


def test_registry_iter_storages():
    fields = list(_registry.iter_storages())

    assert len(fields) == 1
    assert fields[0] is default_storage
