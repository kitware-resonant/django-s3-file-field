from typing import Generator

from django.core import signing
from django.core.files.base import ContentFile, File
from django.core.files.storage import default_storage
import factory
import pytest
from rest_framework.test import APIClient

from s3_file_field._multipart import MultipartManager
from s3_file_field._sizes import mb
from test_app.models import Resource


@pytest.fixture(autouse=True)
def reduce_part_size(mocker):
    """To speed up tests, reduce the part size to the minimum supported by S3 (5MB)."""
    mocker.patch.object(MultipartManager, 'part_size', new=mb(5))


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


class ResourceFactory(factory.Factory):
    class Meta:
        model = Resource

    # Use a unique blob file name for each instance
    blob = factory.Sequence(lambda n: ContentFile(b'test content', name=f'test_key_{n}'))


@pytest.fixture
def resource() -> Resource:
    # Do not save by default
    resource = ResourceFactory.build()
    yield resource
    resource.blob.delete(save=False)


@pytest.fixture
def stored_file_object() -> Generator[File, None, None]:
    """Return a File object, already saved directly into Storage."""
    # Ensure the name is always randomized, even if the key doesn't exist already
    key = default_storage.get_alternative_name('test_key', '')  # type: ignore[attr-defined]
    # In theory, Storage.save can change the key, though this shouldn't happen with a randomized key
    key = default_storage.save(key, ContentFile(b'test content'))
    # Storage.open will return a File object, which knows its size and can access its content
    file_object = default_storage.open(key)
    yield file_object
    default_storage.delete(key)


@pytest.fixture
def field_value(stored_file_object: File) -> str:
    """Return a valid field_value for an existent stored object."""
    return signing.dumps(
        {
            'object_key': stored_file_object.name,
            'file_size': stored_file_object.size,
        }
    )
