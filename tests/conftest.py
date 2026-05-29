from typing import Generator

from django.core.files.base import ContentFile
import factory
import pytest
from pytest_mock import MockerFixture
from rest_framework.test import APIClient, APIRequestFactory

from s3_file_field._multipart import MultipartManager
from s3_file_field._sizes import mb

from test_app.models import Resource

# Explicitly load s3_file_field fixtures, late in Pytest plugin load order.
# If this is auto-loaded via entry point, the import happens before coverage tracing is started by
# pytest-cov, and import-time code doesn't get covered.
# See https://pytest-cov.readthedocs.io/en/latest/plugins.html for a description of the problem.
# See
# https://docs.pytest.org/en/7.1.x/how-to/writing_plugins.html#plugin-discovery-order-at-tool-startup
# for info on Pytest plugin load order.
pytest_plugins = ["s3_file_field.fixtures"]


@pytest.fixture(autouse=True)
def _reduce_part_size(mocker: MockerFixture) -> None:
    """To speed up tests, reduce the part size to the minimum supported by S3 (5MB)."""
    mocker.patch.object(MultipartManager, "part_size", new=mb(5))


@pytest.fixture()
def request_factory() -> APIRequestFactory:
    return APIRequestFactory()


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
