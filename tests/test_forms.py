from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict
import pytest

from s3_file_field.forms import S3FormFileField
from test_app.forms import ResourceForm
from test_app.models import MultiResource

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.core.files import File

    from s3_file_field.fields import S3FileField


def test_form_field_type() -> None:
    form = ResourceForm()
    assert isinstance(form.fields["blob"], S3FormFileField)


def test_form_missing() -> None:
    form = ResourceForm(data={})
    assert not form.is_valid()


def test_form_empty() -> None:
    form = ResourceForm(data={"blob": ""})
    assert not form.is_valid()


def test_form_invalid() -> None:
    form = ResourceForm(data={"blob": "invalid:field_value"})
    assert not form.is_valid()
    assert form.errors.as_data()["blob"][0].code == "invalid"


def test_form_direct_upload_invalid() -> None:
    """Direct file uploads are refused; content must go through the S3 upload flow."""
    form = ResourceForm(
        files=MultiValueDict({"blob": [SimpleUploadedFile("test.txt", b"test content")]})
    )
    assert not form.is_valid()
    assert form.errors.as_data()["blob"][0].code == "invalid"


def test_form_validation(s3ff_field_value: str) -> None:
    form = ResourceForm(data={"blob": s3ff_field_value})
    assert form.is_valid()


def test_form_cross_field_invalid(
    s3ff_field_value_factory: Callable[[File[bytes], S3FileField], str],
    stored_file_object: File[bytes],
) -> None:
    """A FieldValue minted for one S3FileField must not validate on another."""
    other_field = MultiResource._meta.get_field("blob")
    field_value = s3ff_field_value_factory(stored_file_object, other_field)
    form = ResourceForm(data={"blob": field_value})
    assert not form.is_valid()
    assert form.errors.as_data()["blob"][0].code == "invalid"


def test_form_instance(s3ff_field_value: str) -> None:
    form = ResourceForm(data={"blob": s3ff_field_value})

    # full_clean has the side effect of populating instance
    form.full_clean()
    resource = form.instance

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


@pytest.mark.django_db
def test_form_instance_saved(s3ff_field_value: str) -> None:
    form = ResourceForm(data={"blob": s3ff_field_value})

    resource = form.save()
    resource.refresh_from_db()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"
