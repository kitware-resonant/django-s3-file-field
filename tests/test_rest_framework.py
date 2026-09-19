from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ImproperlyConfigured
import pytest
from rest_framework import serializers

from factories import FieldValueFactory, ResourceFactory
from s3_file_field.rest_framework import S3FileSerializerField
from test_app.models import MultiResource, Resource
from test_app.rest import ResourceSerializer

if TYPE_CHECKING:
    from django.core.files import File


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


def test_serializer_field_plain_model_field_explicit() -> None:
    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField(model_field=Resource._meta.get_field("blob"))

    field_value = FieldValueFactory.build()
    serializer = PlainSerializer(data={"blob": field_value.model_dump()})
    assert serializer.is_valid()


def test_serializer_field_plain_model_field_missing() -> None:
    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField()

    serializer = PlainSerializer()
    with pytest.raises(ImproperlyConfigured):
        _ = serializer.fields


def test_serializer_is_valid() -> None:
    field_value = FieldValueFactory.build()
    serializer = ResourceSerializer(data={"blob": field_value.model_dump()})

    assert serializer.is_valid()


def test_serializer_cross_field_invalid() -> None:
    """A FieldValue minted for one S3FileField must not validate on another."""
    other_field_value = FieldValueFactory.build(field_model=MultiResource)
    serializer = ResourceSerializer(data={"blob": other_field_value.model_dump()})

    assert not serializer.is_valid()
    assert serializer.errors["blob"][0].code == "invalid"


def test_serializer_validated_data(stored_file_object: File[bytes]) -> None:
    field_value = FieldValueFactory.build(
        object_key=stored_file_object.name, file_size=stored_file_object.size
    )
    serializer = ResourceSerializer(data={"blob": field_value.model_dump()})
    serializer.is_valid(raise_exception=True)

    assert "blob" in serializer.validated_data
    assert serializer.validated_data["blob"] == stored_file_object.name


@pytest.mark.django_db
def test_serializer_save_create(stored_file_object: File[bytes]) -> None:
    field_value = FieldValueFactory.build(
        object_key=stored_file_object.name, file_size=stored_file_object.size
    )
    serializer = ResourceSerializer(data={"blob": field_value.model_dump()})

    serializer.is_valid(raise_exception=True)
    resource = serializer.save()

    assert resource.blob.name == stored_file_object.name


@pytest.mark.django_db
def test_serializer_save_update(stored_file_object: File[bytes]) -> None:
    field_value = FieldValueFactory.build(
        object_key=stored_file_object.name, file_size=stored_file_object.size
    )
    resource = ResourceFactory.build()
    serializer = ResourceSerializer(resource, data={"blob": field_value.model_dump()})
    # Sanity check
    assert resource.blob.name != stored_file_object.name

    serializer.is_valid(raise_exception=True)
    # save() should modify an existing model instance in-place
    serializer.save()

    assert resource.blob.name == stored_file_object.name
