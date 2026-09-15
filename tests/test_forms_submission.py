from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict
from freezegun import freeze_time
import pytest

from factories import FieldValueFactory, OptionalResourceFactory, ResourceFactory
from form_inspection import field_error_codes
from test_app.forms import (
    DisabledResourceForm,
    LimitedResourceForm,
    MultiResourceForm,
    OptionalResourceForm,
    ResourceForm,
)
from test_app.models import LimitedResource, MultiResource, OptionalResource

if TYPE_CHECKING:
    from django.core.files import File


def test_form_validation(stored_file_object: File[bytes]) -> None:
    field_value = FieldValueFactory.build(
        object_key=stored_file_object.name, file_size=stored_file_object.size
    )
    form = ResourceForm(data={"blob": field_value.model_dump()})

    assert form.is_valid()
    # Validation has the side effect of populating the instance
    with form.instance.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


def test_form_validation_prefixed() -> None:
    """A form prefix (as used by formsets and admin inlines) is applied to the field name."""
    field_value = FieldValueFactory.build()
    form = ResourceForm(data={"prefix-blob": field_value.model_dump()}, prefix="prefix")

    assert form.is_valid()


def test_form_validation_duplicate_entries() -> None:
    """When a wire entry is duplicated, only the last value is used."""
    field_value_str = cast("str", FieldValueFactory.build().model_dump())
    data = QueryDict(mutable=True)
    data.setlist("blob", ["", field_value_str])
    form = ResourceForm(data=data)

    assert form.is_valid()


def test_form_validation_oversized() -> None:
    """A signed value larger than the field's max_size is accepted.

    Size limits are enforced when the upload is initiated and finalized; a signed
    FieldValue attests that they were satisfied at signing time.
    """
    field_value = FieldValueFactory.build(field_model=LimitedResource, file_size=100)
    form = LimitedResourceForm(data={"blob": field_value.model_dump()})

    assert form.is_valid()


def test_form_create_missing() -> None:
    """On a create form, an omitted value fails validation for a required field."""
    form = ResourceForm(data={})

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["required"]


def test_form_create_empty() -> None:
    """On a create form, an explicit empty value is refused, as there is nothing to clear."""
    form = ResourceForm(data={"blob": ""})

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]


def test_form_invalid() -> None:
    form = ResourceForm(data={"blob": "invalid:field_value"})
    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]


def test_form_invalid_whitespace() -> None:
    """A whitespace-only value is treated as a (rejected) value, not as a clear."""
    form = ResourceForm(data={"blob": "   "})

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]


def test_form_invalid_expired() -> None:
    """A signed value older than its maximum age is rejected."""
    with freeze_time("2020-01-01"):
        # The signing timestamp is minted at serialization time
        field_value_str = FieldValueFactory.build().model_dump()
    form = ResourceForm(data={"blob": field_value_str})

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]


def test_form_invalid_file_name_length() -> None:
    """A signed value with an overlong file name is rejected."""
    field_value = FieldValueFactory.build(object_key="x" * 3000)
    form = ResourceForm(data={"blob": field_value.model_dump()})

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["max_length"]


def test_form_invalid_file_name_empty() -> None:
    """A signed value with an empty file name is rejected."""
    field_value = FieldValueFactory.build(object_key="")
    form = ResourceForm(data={"blob": field_value.model_dump()})

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]


def test_form_multiple_fields() -> None:
    """Multiple S3FileFields on one form each accept a value minted for them."""
    blob_field_value = FieldValueFactory.build(
        field_model=MultiResource, field_name="blob", object_key="key/file.txt"
    )
    optional_blob_field_value = FieldValueFactory.build(
        field_model=MultiResource, field_name="optional_blob", object_key="key/optional_file.txt"
    )
    form = MultiResourceForm(
        data={
            "blob": blob_field_value.model_dump(),
            "optional_blob": optional_blob_field_value.model_dump(),
        }
    )

    assert form.is_valid()
    assert form.instance.blob.name == "key/file.txt"
    assert form.instance.optional_blob.name == "key/optional_file.txt"


def test_form_cross_field_invalid() -> None:
    """A FieldValue minted for one S3FileField must not validate on another."""
    other_field_value = FieldValueFactory.build(field_model=OptionalResource)
    form = ResourceForm(data={"blob": other_field_value.model_dump()})

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]


def test_form_multiple_fields_swapped() -> None:
    """Values are not interchangeable, even between sibling fields on the same form."""
    blob_field_value = FieldValueFactory.build(field_model=MultiResource, field_name="blob")
    optional_blob_field_value = FieldValueFactory.build(
        field_model=MultiResource, field_name="optional_blob"
    )
    form = MultiResourceForm(
        data={
            "blob": optional_blob_field_value.model_dump(),
            "optional_blob": blob_field_value.model_dump(),
        }
    )

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]
    assert field_error_codes(form, "optional_blob") == ["invalid"]


def test_form_direct_upload_invalid() -> None:
    """Direct file uploads are refused; content must go through the S3 upload flow."""
    form = ResourceForm(
        files=MultiValueDict({"blob": [SimpleUploadedFile("test.txt", b"test content")]})
    )

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["invalid"]


def test_form_direct_upload_with_value() -> None:
    """A submitted value takes precedence over an accompanying direct file upload."""
    field_value = FieldValueFactory.build(object_key="key/file.txt")
    form = ResourceForm(
        data={"blob": field_value.model_dump()},
        files=MultiValueDict({"blob": [SimpleUploadedFile("other.txt", b"other content")]}),
    )

    assert form.is_valid()
    assert form.instance.blob.name == "key/file.txt"


def test_form_edit_keep() -> None:
    """On an edit form, an omitted value signals to keep the existing value."""
    instance = OptionalResourceFactory.build(blob="key/file.txt")
    form = OptionalResourceForm(data={}, instance=instance)

    assert form.is_valid()
    assert form.cleaned_data["blob"] == instance.blob
    assert form.instance.blob.name == "key/file.txt"


def test_form_edit_clear() -> None:
    """On an edit form, an explicit empty value signals to clear the existing value."""
    instance = OptionalResourceFactory.build(blob="key/file.txt")
    form = OptionalResourceForm(data={"blob": ""}, instance=instance)

    assert form.is_valid()
    assert form.cleaned_data["blob"] is False
    assert form.instance.blob.name == ""


def test_form_edit_clear_required() -> None:
    """On an edit form, clearing a required field is refused, keeping the existing value."""
    instance = ResourceFactory.build(blob="key/file.txt")
    form = ResourceForm(data={"blob": ""}, instance=instance)

    assert not form.is_valid()
    assert field_error_codes(form, "blob") == ["required"]
    assert form.instance.blob.name == "key/file.txt"


def test_form_edit_replace() -> None:
    """On an edit form, a valid submitted value replaces the existing value."""
    instance = ResourceFactory.build(blob="old_key/file.txt")
    field_value = FieldValueFactory.build(object_key="key/file.txt")
    form = ResourceForm(data={"blob": field_value.model_dump()}, instance=instance)

    assert form.is_valid()
    # The field now references the newly uploaded object
    assert form.instance.blob.name == "key/file.txt"


def test_form_edit_disabled() -> None:
    """A disabled field ignores even a valid submitted value, keeping the existing value."""
    instance = ResourceFactory.build(blob="key/file.txt")
    field_value = FieldValueFactory.build()
    form = DisabledResourceForm(data={"blob": field_value.model_dump()}, instance=instance)

    assert form.is_valid()
    assert form.cleaned_data["blob"] == instance.blob
    assert form.instance.blob.name == "key/file.txt"


@pytest.mark.django_db
def test_form_instance_saved(stored_file_object: File[bytes]) -> None:
    field_value = FieldValueFactory.build(
        object_key=stored_file_object.name, file_size=stored_file_object.size
    )
    form = ResourceForm(data={"blob": field_value.model_dump()})

    resource = form.save()
    resource.refresh_from_db()

    # The stored object is referenced directly, not copied or re-uploaded
    assert resource.blob.name == stored_file_object.name
    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"
