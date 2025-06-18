import re

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
import pytest

from test_app.models import Resource
from s3_file_field.widgets import S3PlaceholderFile


@pytest.mark.django_db()
def test_fields_save(resource: Resource) -> None:
    resource.save()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


def test_fields_save_field() -> None:
    resource = Resource()
    # Upload the file, but do not save the model instance
    resource.blob.save("test_key", ContentFile(b"test content"), save=False)
    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"
    resource.blob.delete(save=False)


@pytest.mark.django_db()
def test_fields_save_refresh(resource: Resource) -> None:
    resource.save()
    resource.refresh_from_db()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


@pytest.mark.django_db()
def test_fields_save_uuid_prefix(resource: Resource) -> None:
    resource.save()

    assert re.search(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test_key_",
        resource.blob.name,
    )


def test_fields_clean(resource: Resource) -> None:
    resource.full_clean()


@pytest.mark.django_db()
def test_fields_clean_refresh(resource: Resource) -> None:
    resource.save()
    resource.refresh_from_db()
    resource.full_clean()


def test_fields_clean_empty() -> None:
    resource = Resource()
    with pytest.raises(ValidationError, match=r"This field cannot be blank\."):
        resource.full_clean()


def test_fields_check_success(resource: Resource) -> None:
    assert resource._meta.get_field("blob").check() == []


def test_s3_placeholder_file_save_form_data() -> None:
    resource = Resource()
    blob_field = resource._meta.get_field("blob")
    placeholder_file = S3PlaceholderFile(name="test-file.txt")
    blob_field.save_form_data(resource, placeholder_file)
    assert getattr(resource, blob_field.attname) == "test-file.txt"


@pytest.mark.django_db()
def test_s3_placeholder_file_save_form_data_with_save() -> None:
    resource = Resource()
    blob_field = resource._meta.get_field("blob")
    placeholder_file = S3PlaceholderFile(name="test-file-save.txt")
    blob_field.save_form_data(resource, placeholder_file)
    resource.save()
    resource.refresh_from_db()
    assert resource.blob.name == "test-file-save.txt"
