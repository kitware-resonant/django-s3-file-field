from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from test_app.drf import ResourceSerializer

if TYPE_CHECKING:
    from django.core.files import File

    from test_app.models import Resource


def test_serializer_data_missing() -> None:
    serializer = ResourceSerializer(
        data={
            # Omitted field
        }
    )

    assert not serializer.is_valid()
    assert serializer.errors["blob"][0].code == "required"


def test_serializer_data_invalid() -> None:
    serializer = ResourceSerializer(
        data={
            # Invalid, this must be a signed field_value
            "blob": "test_key"
        }
    )

    assert not serializer.is_valid()
    assert serializer.errors["blob"][0].code == "invalid"


def test_serializer_is_valid(s3ff_field_value: str) -> None:
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})

    assert serializer.is_valid()


def test_serializer_validated_data(stored_file_object: File[bytes], s3ff_field_value: str) -> None:
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})
    serializer.is_valid(raise_exception=True)

    assert "blob" in serializer.validated_data
    # The field_value fixture is created from the same stored_file_object
    assert serializer.validated_data["blob"] == stored_file_object.name


@pytest.mark.django_db()
def test_serializer_save_create(stored_file_object: File[bytes], s3ff_field_value: str) -> None:
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})

    serializer.is_valid(raise_exception=True)
    resource = serializer.save()

    assert resource.blob.name == stored_file_object.name


@pytest.mark.django_db()
def test_serializer_save_update(
    resource: Resource, stored_file_object: File[bytes], s3ff_field_value: str
) -> None:
    serializer = ResourceSerializer(resource, data={"blob": s3ff_field_value})
    # Sanity check
    assert resource.blob.name != stored_file_object.name

    serializer.is_valid(raise_exception=True)
    # save() should modify an existing model instance in-place
    serializer.save()

    assert resource.blob.name == stored_file_object.name
