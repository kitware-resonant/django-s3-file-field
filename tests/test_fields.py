import re

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
import pytest

from test_app.models import Resource


@pytest.mark.django_db()
def test_fields_save(resource):
    resource.save()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


def test_fields_save_field():
    resource = Resource()
    # Upload the file, but do not save the model instance
    resource.blob.save("test_key", ContentFile(b"test content"), save=False)
    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"
    resource.blob.delete(save=False)


@pytest.mark.django_db()
def test_fields_save_refresh(resource):
    resource.save()
    resource.refresh_from_db()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


@pytest.mark.django_db()
def test_fields_save_uuid_prefix(resource):
    resource.save()

    assert re.search(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test_key_",
        resource.blob.name,
    )


def test_fields_clean(resource):
    resource.full_clean()


@pytest.mark.django_db()
def test_fields_clean_refresh(resource):
    resource.save()
    resource.refresh_from_db()
    resource.full_clean()


def test_fields_clean_empty():
    resource = Resource()
    with pytest.raises(ValidationError, match=r"This field cannot be blank\."):
        resource.full_clean()
