from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from django.core.files.base import ContentFile
import factory
import pytest
from rest_framework.test import APIClient

from s3_file_field._multipart import MultipartManager
from s3_file_field._pydantic_utils import SignedModel
from s3_file_field._schemas import UploadToken
from s3_file_field._sizes import mb
from test_app.models import Resource

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from django.core.files import File
    from pytest_mock import MockerFixture

    from s3_file_field.fields import S3FileField

# Explicitly load s3_file_field fixtures, late in Pytest plugin load order.
# If this is auto-loaded via entry point, the import happens before coverage tracing is started by
# pytest-cov, and import-time code doesn't get covered.
# See https://pytest-cov.readthedocs.io/en/latest/plugins.html for a description of the problem.
# See
# https://docs.pytest.org/en/7.1.x/how-to/writing_plugins.html#plugin-discovery-order-at-tool-startup
# for info on Pytest plugin load order.
pytest_plugins = ["s3_file_field.fixtures"]


@pytest.fixture(autouse=True)
def _reduce_baseline_part_size(mocker: MockerFixture) -> None:
    """To speed up tests, reduce the baseline part size to the minimum supported by S3 (5MB)."""
    mocker.patch.object(MultipartManager, "baseline_part_size", new=mb(5))


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def s3ff_field_value(
    s3ff_field_value_factory: Callable[[File[bytes], S3FileField], str],
    stored_file_object: File[bytes],
) -> str:
    """Return a valid field_value for Resource.blob, for an existent File."""
    return s3ff_field_value_factory(stored_file_object, Resource._meta.get_field("blob"))


class ResourceFactory(factory.Factory[Resource]):
    class Meta:
        model = Resource

    # Use a unique blob file name for each instance
    blob = factory.Sequence(lambda n: ContentFile(b"test content", name=f"test_key_{n}"))


@pytest.fixture
def resource() -> Generator[Resource]:
    # Do not save by default
    resource = ResourceFactory.build()
    yield resource
    resource.blob.delete(save=False)


class SignedModelFactory[T: SignedModel](factory.Factory[T]):
    class Meta:
        abstract = True

    @classmethod
    def _build(cls, model_class: type[T], *args: Any, **kwargs: Any) -> T:
        # SignedModel field values cannot be passed directly to __init__, as its wrap
        # validator would attempt to unsign them; use model_construct, as the library does.
        return model_class.model_construct(*args, **kwargs)


class UploadTokenFactory(SignedModelFactory[UploadToken]):
    class Meta:
        model = UploadToken

    field = factory.LazyFunction(lambda: Resource._meta.get_field("blob"))
    upload_id: factory.Faker[UploadToken, str] = factory.Faker("uuid4")
    object_key = factory.Sequence(lambda n: f"{uuid4()}/test-{n}.jpg")


@pytest.fixture
def upload_token() -> UploadToken:
    return UploadTokenFactory.build()
