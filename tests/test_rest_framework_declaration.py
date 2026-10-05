from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured
import pytest
from rest_framework import serializers

from factories import FieldValueFactory
from s3_file_field.rest_framework import S3FileSerializerField
from test_app.models import OptionalResource, Resource
from test_app.rest import OptionalResourceSerializer, ResourceSerializer


def test_serializer_field_type() -> None:
    """A ModelSerializer uses the serializer field for an S3FileField automatically."""
    assert isinstance(ResourceSerializer().fields["blob"], S3FileSerializerField)


def test_serializer_field_required() -> None:
    """A ModelSerializer derives whether the field is required from the model field."""
    assert ResourceSerializer().fields["blob"].required is True
    assert OptionalResourceSerializer().fields["blob"].required is False


def test_serializer_field_allow_null() -> None:
    """Whether the field may be cleared is derived from the model field's "blank"."""
    assert ResourceSerializer().fields["blob"].allow_null is False
    assert OptionalResourceSerializer().fields["blob"].allow_null is True


def test_serializer_field_allow_null_explicit() -> None:
    """An explicit "allow_null" takes precedence over the model field, in either direction."""

    class ClearableResourceSerializer(ResourceSerializer):
        class Meta(ResourceSerializer.Meta):
            extra_kwargs = {"blob": {"allow_null": True}}

    class UnclearableOptionalResourceSerializer(OptionalResourceSerializer):
        class Meta(OptionalResourceSerializer.Meta):
            extra_kwargs = {"blob": {"allow_null": False}}

    assert ClearableResourceSerializer().fields["blob"].allow_null is True
    assert UnclearableOptionalResourceSerializer().fields["blob"].allow_null is False


def test_serializer_field_plain_model_field_explicit() -> None:
    """On a plain Serializer, the field is configured by its explicitly given model field."""

    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField(model_field=Resource._meta.get_field("blob"))
        # Unlike a ModelSerializer, a plain Serializer leaves "required" to the author
        optional_blob = S3FileSerializerField(
            model_field=OptionalResource._meta.get_field("blob"), required=False
        )

    field_value = FieldValueFactory.build()
    serializer = PlainSerializer(data={"blob": field_value.model_dump()})

    assert serializer.is_valid()
    # Whether the field may be cleared is derived from the model field, as in a ModelSerializer
    assert serializer.fields["blob"].allow_null is False
    assert serializer.fields["optional_blob"].allow_null is True


def test_serializer_field_plain_model_field_missing() -> None:
    """On a plain Serializer, a writable field without a model field is a configuration error."""

    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField()

    serializer = PlainSerializer()

    with pytest.raises(ImproperlyConfigured):
        _ = serializer.fields


def test_serializer_field_plain_read_only() -> None:
    """A read-only field never validates input, so it needs no model field."""

    class PlainSerializer(serializers.Serializer[Any]):
        blob = S3FileSerializerField(read_only=True)

    serializer = PlainSerializer()

    assert "blob" in serializer.fields
