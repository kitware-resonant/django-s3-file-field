from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from factories import (
    FieldValueFactory,
    OptionalResourceFactory,
    ResourceFactory,
    ValidatedResourceFactory,
)
from serializer_inspection import field_error_codes
from test_app.models import (
    LimitedResource,
    MultiResource,
    OptionalResource,
    Resource,
    ValidatedResource,
)
from test_app.rest import (
    LimitedResourceSerializer,
    MultiResourceSerializer,
    OptionalResourceSerializer,
    ResourceSerializer,
    ValidatedResourceSerializer,
)

if TYPE_CHECKING:
    from django.core.files import File
    from pytest_mock import MockerFixture


def test_serializer_validation() -> None:
    field_value = FieldValueFactory.build(object_key="key/file.txt", file_size=15)
    serializer = ResourceSerializer(data={"blob": field_value.model_dump()})

    assert serializer.is_valid()
    # The validated value describes the stored object, as a "validate_<field>" method would need
    assert serializer.validated_data["blob"].name == "key/file.txt"
    assert serializer.validated_data["blob"].size == 15


def test_serializer_validation_content(stored_file_object: File[bytes]) -> None:
    """The validated value's content is readable from storage, as a validator may need."""
    field_value = FieldValueFactory.build(
        object_key=stored_file_object.name, file_size=stored_file_object.size
    )
    serializer = ResourceSerializer(data={"blob": field_value.model_dump()})

    assert serializer.is_valid()
    with serializer.validated_data["blob"].open() as blob_stream:
        assert blob_stream.read() == b"test content"


def test_serializer_create_missing() -> None:
    """On a create, an omitted value fails validation for a required field."""
    serializer = ResourceSerializer(data={})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["required"]


def test_serializer_create_empty() -> None:
    """On a create, an empty value is equivalent to an omitted one."""
    serializer = ResourceSerializer(data={"blob": ""})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["required"]


def test_serializer_create_missing_optional() -> None:
    """On a create, an omitted value is accepted for an optional field, which stays empty."""
    serializer = OptionalResourceSerializer(data={})

    assert serializer.is_valid()
    assert "blob" not in serializer.validated_data


def test_serializer_create_clear() -> None:
    """On a create, a clear of a required field is refused."""
    serializer = ResourceSerializer(data={"blob": "s3ff:clear"})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["null"]


def test_serializer_create_clear_optional() -> None:
    """On a create, a clear of an optional field is a no-op, as there is nothing to clear."""
    serializer = OptionalResourceSerializer(data={"blob": "s3ff:clear"})

    assert serializer.is_valid()
    assert serializer.validated_data["blob"] is None


def test_serializer_update_missing() -> None:
    """On a full update, an omitted value fails validation for a required field, as DRF does."""
    resource = ResourceFactory.build(blob="key/file.txt")
    serializer = ResourceSerializer(resource, data={})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["required"]


def test_serializer_update_empty() -> None:
    """On a full update, an empty value is equivalent to an omitted one, failing if required."""
    resource = ResourceFactory.build(blob="key/file.txt")
    serializer = ResourceSerializer(resource, data={"blob": ""})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["required"]


def test_serializer_update_missing_partial() -> None:
    """On a partial update, an omitted value keeps the existing value."""
    resource = ResourceFactory.build(blob="key/file.txt")
    serializer = ResourceSerializer(resource, data={}, partial=True)

    assert serializer.is_valid()
    assert "blob" not in serializer.validated_data


def test_serializer_update_empty_partial() -> None:
    """On a partial update, an empty value keeps the existing value."""
    resource = ResourceFactory.build(blob="key/file.txt")
    serializer = ResourceSerializer(resource, data={"blob": ""}, partial=True)

    assert serializer.is_valid()
    assert "blob" not in serializer.validated_data


def test_serializer_update_clear() -> None:
    """On an update, the clear value clears the existing value."""
    resource = OptionalResourceFactory.build(blob="key/file.txt")
    serializer = OptionalResourceSerializer(resource, data={"blob": "s3ff:clear"})

    assert serializer.is_valid()
    assert serializer.validated_data["blob"] is None


def test_serializer_update_clear_null() -> None:
    """On an update, null is equivalent to the clear value, as DRF unsets a file field."""
    resource = OptionalResourceFactory.build(blob="key/file.txt")
    serializer = OptionalResourceSerializer(resource, data={"blob": None})

    assert serializer.is_valid()
    assert serializer.validated_data["blob"] is None


def test_serializer_update_clear_required() -> None:
    """On an update, clearing a required field is refused."""
    resource = ResourceFactory.build(blob="key/file.txt")
    serializer = ResourceSerializer(resource, data={"blob": "s3ff:clear"})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["null"]


def test_serializer_update_replace() -> None:
    """On an update, a valid submitted value replaces the existing value."""
    resource = ResourceFactory.build(blob="old_key/file.txt")
    field_value = FieldValueFactory.build(object_key="key/file.txt")
    serializer = ResourceSerializer(resource, data={"blob": field_value.model_dump()})

    assert serializer.is_valid()
    assert serializer.validated_data["blob"].name == "key/file.txt"


def test_serializer_invalid() -> None:
    serializer = ResourceSerializer(data={"blob": "invalid:field_value"})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["invalid"]


def test_serializer_invalid_whitespace() -> None:
    """A whitespace-only value is treated as a (rejected) value, not as an empty one."""
    serializer = ResourceSerializer(data={"blob": "   "})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["invalid"]


def test_serializer_invalid_file_name_length() -> None:
    """A signed value with an overlong file name is rejected."""
    field_value = FieldValueFactory.build(object_key="x" * 3000)
    serializer = ResourceSerializer(data={"blob": field_value.model_dump()})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["max_length"]


def test_serializer_multiple_fields() -> None:
    """Multiple S3FileFields on one serializer each accept a value minted for them."""
    blob_field_value = FieldValueFactory.build(
        field_model=MultiResource, field_name="blob", object_key="key/file.txt"
    )
    optional_blob_field_value = FieldValueFactory.build(
        field_model=MultiResource, field_name="optional_blob", object_key="key/optional_file.txt"
    )
    serializer = MultiResourceSerializer(
        data={
            "blob": blob_field_value.model_dump(),
            "optional_blob": optional_blob_field_value.model_dump(),
        }
    )

    assert serializer.is_valid()
    assert serializer.validated_data["blob"].name == "key/file.txt"
    assert serializer.validated_data["optional_blob"].name == "key/optional_file.txt"


def test_serializer_cross_field_invalid() -> None:
    """A FieldValue minted for one S3FileField must not validate on another."""
    other_field_value = FieldValueFactory.build(field_model=OptionalResource)
    serializer = ResourceSerializer(data={"blob": other_field_value.model_dump()})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["invalid"]


def test_serializer_multiple_fields_swapped() -> None:
    """Values are not interchangeable, even between sibling fields on the same serializer."""
    blob_field_value = FieldValueFactory.build(field_model=MultiResource, field_name="blob")
    optional_blob_field_value = FieldValueFactory.build(
        field_model=MultiResource, field_name="optional_blob"
    )
    serializer = MultiResourceSerializer(
        data={
            "blob": optional_blob_field_value.model_dump(),
            "optional_blob": blob_field_value.model_dump(),
        }
    )

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["invalid"]
    assert field_error_codes(serializer, "optional_blob") == ["invalid"]


def test_serializer_direct_upload_invalid() -> None:
    """Direct file uploads are refused; content must go through the S3 upload flow."""
    serializer = ResourceSerializer(data={"blob": SimpleUploadedFile("test.txt", b"test content")})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["invalid"]


def test_serializer_validation_oversized() -> None:
    """A signed value larger than the field's max_size is accepted.

    Size limits are enforced when the upload is initiated and finalized; a signed
    FieldValue attests that they were satisfied at signing time.
    """
    field_value = FieldValueFactory.build(field_model=LimitedResource, file_size=100)
    serializer = LimitedResourceSerializer(data={"blob": field_value.model_dump()})

    assert serializer.is_valid()


def test_serializer_validation_model_validators() -> None:
    """The model field's validators run against the validated value, as a ModelSerializer does."""
    field_value = FieldValueFactory.build(field_model=ValidatedResource, object_key="key/file.txt")
    serializer = ValidatedResourceSerializer(data={"blob": field_value.model_dump()})

    assert serializer.is_valid()


def test_serializer_validation_model_validators_invalid() -> None:
    """A value refused by the model field's validators fails with their error."""
    field_value = FieldValueFactory.build(field_model=ValidatedResource, object_key="key/file.pdf")
    serializer = ValidatedResourceSerializer(data={"blob": field_value.model_dump()})

    assert not serializer.is_valid()
    assert field_error_codes(serializer, "blob") == ["invalid_extension"]


def test_serializer_update_clear_model_validators() -> None:
    """Clearing an optional field never reaches the model field's validators."""
    resource = ValidatedResourceFactory.build(blob="key/file.txt")
    serializer = ValidatedResourceSerializer(resource, data={"blob": "s3ff:clear"})

    assert serializer.is_valid()
    assert serializer.validated_data["blob"] is None


@pytest.mark.django_db
def test_serializer_save_create(mocker: MockerFixture) -> None:
    field_value = FieldValueFactory.build(object_key="key/file.txt")
    serializer = ResourceSerializer(data={"blob": field_value.model_dump()})
    storage_save = mocker.spy(Resource._meta.get_field("blob").storage, "save")

    serializer.is_valid(raise_exception=True)
    resource = serializer.save()
    resource.refresh_from_db()

    # The stored object is referenced directly, not copied or re-uploaded
    assert resource.blob.name == "key/file.txt"
    storage_save.assert_not_called()


@pytest.mark.django_db
def test_serializer_save_update(mocker: MockerFixture) -> None:
    field_value = FieldValueFactory.build(object_key="key/file.txt")
    resource = ResourceFactory.build(blob="old_key/file.txt")
    resource.save()
    serializer = ResourceSerializer(resource, data={"blob": field_value.model_dump()})
    storage_save = mocker.spy(Resource._meta.get_field("blob").storage, "save")

    serializer.is_valid(raise_exception=True)
    # save() modifies the existing model instance in place
    serializer.save()
    resource.refresh_from_db()

    # The stored object is referenced directly, not copied or re-uploaded
    assert resource.blob.name == "key/file.txt"
    storage_save.assert_not_called()


@pytest.mark.django_db
def test_serializer_save_update_clear() -> None:
    resource = OptionalResourceFactory.build(blob="key/file.txt")
    resource.save()
    serializer = OptionalResourceSerializer(resource, data={"blob": "s3ff:clear"})

    serializer.is_valid(raise_exception=True)
    serializer.save()
    resource.refresh_from_db()

    assert not resource.blob
