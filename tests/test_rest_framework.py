from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ImproperlyConfigured
import pytest
from rest_framework import serializers

from s3_file_field.rest_framework import S3FileSerializerField
from test_app.models import MultiResource, Resource
from test_app.rest import ResourceSerializer

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.core.files import File

    from s3_file_field.fields import S3FileField


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


def test_serializer_field_plain_read_only() -> None:
    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField(read_only=True)

    serializer = PlainSerializer()
    assert "blob" in serializer.fields


def test_serializer_field_plain_model_field_explicit(s3ff_field_value: str) -> None:
    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField(model_field=Resource._meta.get_field("blob"))

    serializer = PlainSerializer(data={"blob": s3ff_field_value})
    assert serializer.is_valid()


def test_serializer_field_plain_model_field_missing() -> None:
    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField()

    serializer = PlainSerializer()
    with pytest.raises(ImproperlyConfigured):
        _ = serializer.fields


def test_serializer_is_valid(s3ff_field_value: str) -> None:
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})

    assert serializer.is_valid()


def test_serializer_cross_field_invalid(
    s3ff_field_value_factory: Callable[[File[bytes], S3FileField], str],
    stored_file_object: File[bytes],
) -> None:
    """A FieldValue minted for one S3FileField must not validate on another."""
    other_field = MultiResource._meta.get_field("blob")
    field_value = s3ff_field_value_factory(stored_file_object, other_field)
    serializer = ResourceSerializer(data={"blob": field_value})

    assert not serializer.is_valid()
    assert serializer.errors["blob"][0].code == "invalid"


def test_serializer_validated_data(stored_file_object: File[bytes], s3ff_field_value: str) -> None:
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})
    serializer.is_valid(raise_exception=True)

    assert "blob" in serializer.validated_data
    # The field_value fixture is created from the same stored_file_object
    assert serializer.validated_data["blob"] == stored_file_object.name


@pytest.mark.django_db
def test_serializer_save_create(stored_file_object: File[bytes], s3ff_field_value: str) -> None:
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})

    serializer.is_valid(raise_exception=True)
    resource = serializer.save()

    assert resource.blob.name == stored_file_object.name


@pytest.mark.django_db
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
