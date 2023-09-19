from typing import Generator

from django.core.files.base import ContentFile
import factory
import pytest
from rest_framework.test import APIClient

from s3_file_field._multipart import MultipartManager
from s3_file_field._sizes import mb

from test_app.models import Resource


@pytest.fixture(autouse=True)
def _reduce_part_size(mocker):
    """To speed up tests, reduce the part size to the minimum supported by S3 (5MB)."""
    mocker.patch.object(MultipartManager, "part_size", new=mb(5))


@pytest.fixture()
def api_client() -> APIClient:
    return APIClient()


class ResourceFactory(factory.Factory):
    class Meta:
        model = Resource

    # Use a unique blob file name for each instance
    blob = factory.Sequence(lambda n: ContentFile(b"test content", name=f"test_key_{n}"))


@pytest.fixture()
def resource() -> Generator[Resource, None, None]:
    # Do not save by default
    resource = ResourceFactory.build()
    yield resource
    resource.blob.delete(save=False)
