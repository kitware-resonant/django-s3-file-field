from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import override_settings
import pytest

from s3_file_field._sizes import gb
from test_app.models import LimitedResource, Resource


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_fields_save_refresh(resource: Resource) -> None:
    resource.save()
    resource.refresh_from_db()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


@pytest.mark.django_db
def test_fields_save_uuid_prefix(resource: Resource) -> None:
    resource.save()

    assert resource.blob.name is not None
    assert re.search(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test_key_",
        resource.blob.name,
    )


def test_fields_clean(resource: Resource) -> None:
    resource.full_clean()


@pytest.mark.django_db
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


def test_fields_max_size_default() -> None:
    field = Resource._meta.get_field("blob")
    assert field.max_size is None
    # For MinIO, the 10,000 x 5 GB part limit is lower than the 50 TB maximum object size
    assert field.effective_max_size == gb(50_000)


def test_fields_max_size_explicit() -> None:
    field = LimitedResource._meta.get_field("blob")
    assert field.max_size == 10
    assert field.effective_max_size == 10


@override_settings(S3_FILE_FIELD_MAX_SIZE=5)
def test_fields_max_size_setting() -> None:
    assert Resource._meta.get_field("blob").effective_max_size == 5
    assert LimitedResource._meta.get_field("blob").effective_max_size == 10


@override_settings(S3_FILE_FIELD_MAX_SIZE=None)
def test_fields_max_size_setting_none() -> None:
    assert Resource._meta.get_field("blob").effective_max_size == gb(50_000)
