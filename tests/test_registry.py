import inspect
import sys
from typing import Generator, cast

from django.core.files.storage import default_storage
from django.db import models
import pytest

from s3_file_field import _registry
from s3_file_field.fields import S3FileField
from test_app.models import Resource


@pytest.fixture()
def s3ff_field() -> S3FileField:
    """Return an attached S3FileField (not S3FieldFile) instance."""
    return cast(S3FileField, Resource._meta.get_field("blob"))


@pytest.fixture()
def ephemeral_s3ff_field() -> Generator[S3FileField, None, None]:
    # Declaring this will implicitly register the field
    class EphemeralResource(models.Model):
        class Meta:
            app_label = "test_app"

        blob = S3FileField()

    field = cast(S3FileField, EphemeralResource._meta.get_field("blob"))
    yield field
    # The registry state is global to the process, so attempt to clean up
    del _registry._fields[field.id]


def test_field_id(s3ff_field: S3FileField) -> None:
    assert s3ff_field.id == "test_app.Resource.blob"


def test_field_id_premature() -> None:
    s3ff_field = S3FileField()
    with pytest.raises(Exception, match=r"contribute_to_class"):
        s3ff_field.id  # noqa:B018


def test_registry_get_field(s3ff_field: S3FileField) -> None:
    assert _registry.get_field(s3ff_field.id) is s3ff_field


def test_registry_iter_fields(s3ff_field: S3FileField) -> None:
    fields = list(_registry.iter_fields())

    assert len(fields) == 3
    assert any(field is s3ff_field for field in fields)


def test_registry_iter_storages() -> None:
    fields = list(_registry.iter_storages())

    assert len(fields) == 1
    assert fields[0] is default_storage


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Bug bpo-35113")
def test_registry_register_field_multiple(ephemeral_s3ff_field: S3FileField) -> None:
    with pytest.warns(
        RuntimeWarning, match=r"Overwriting existing S3FileField declaration"
    ) as records:
        # Try to create a field with the same id
        class EphemeralResource(models.Model):
            class Meta:
                app_label = "test_app"

            blob = S3FileField()

    # Ensure the warning is attributed to the re-defined model, since stacklevel is set empirically
    warning = next(record for record in records if str(record.message).startswith("Overwriting"))
    assert warning.filename == inspect.getsourcefile(EphemeralResource)
    assert warning.lineno == inspect.getsourcelines(EphemeralResource)[1]

    duplicate_field = cast(S3FileField, EphemeralResource._meta.get_field("blob"))
    # Sanity check
    assert duplicate_field.id == ephemeral_s3ff_field.id
    assert duplicate_field is not ephemeral_s3ff_field
    # The most recently registered field should by stored
    assert _registry.get_field(duplicate_field.id) is duplicate_field
