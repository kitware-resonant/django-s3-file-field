import re

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
import pytest


@pytest.mark.django_db
def test_fields_save(resource):
    resource.blob = ContentFile(b'test content', name='test_key')
    resource.save()
    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b'test content'


def test_fields_save_field(resource):
    # Upload the file, but do not save the model instance
    resource.blob.save('test_key', ContentFile(b'test content'), save=False)
    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b'test content'


@pytest.mark.django_db
def test_fields_save_refresh(resource):
    resource.blob = ContentFile(b'test content', name='test_key')
    resource.save()
    resource.refresh_from_db()
    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b'test content'


@pytest.mark.django_db
def test_fields_save_uuid_prefix(resource):
    resource.blob = ContentFile(b'test content', name='test_key')
    resource.save()
    assert re.match(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test_key', resource.blob.name
    )


def test_fields_clean(resource):
    resource.blob = ContentFile(b'test content', name='test_key')
    resource.full_clean()


@pytest.mark.django_db
def test_fields_clean_refresh(resource):
    resource.blob = ContentFile(b'test content', name='test_key')
    resource.save()
    resource.refresh_from_db()
    resource.full_clean()


def test_fields_clean_empty(resource):
    with pytest.raises(ValidationError, match=r'This field cannot be blank\.'):
        resource.full_clean()
