from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from django.core.files.base import ContentFile
import factory

from s3_file_field._pydantic_utils import SignedModel
from s3_file_field._schemas import FieldValue, UploadToken
from test_app.models import MultiResource, OptionalResource, Resource

if TYPE_CHECKING:
    from django.db.models import Model

    from s3_file_field.fields import S3FileField


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

    class Params:
        field_model: type[Model] = Resource

    field: factory.LazyAttribute[UploadToken, S3FileField] = factory.LazyAttribute(
        lambda o: o.field_model._meta.get_field("blob")
    )
    upload_id: factory.Faker[UploadToken, str] = factory.Faker("uuid4")
    object_key = factory.Sequence(lambda n: f"{uuid4()}/test-{n}.jpg")


class FieldValueFactory(SignedModelFactory[FieldValue]):
    class Meta:
        model = FieldValue

    class Params:
        field_model: type[Model] = Resource
        field_name: str = "blob"

    field: factory.LazyAttribute[FieldValue, S3FileField] = factory.LazyAttribute(
        lambda o: o.field_model._meta.get_field(o.field_name)
    )
    object_key = factory.Sequence(lambda n: f"{uuid4()}/test-{n}.jpg")
    file_size = 12


def _content_file(n: int) -> ContentFile[bytes]:
    """Return an unsaved file with a unique name, as the default for model file fields."""
    return ContentFile(b"test content", name=f"test_key_{n}")


class ResourceFactory(factory.Factory[Resource]):
    class Meta:
        model = Resource

    blob = factory.Sequence(_content_file)


class OptionalResourceFactory(factory.Factory[OptionalResource]):
    class Meta:
        model = OptionalResource

    blob = factory.Sequence(_content_file)


class MultiResourceFactory(factory.Factory[MultiResource]):
    class Meta:
        model = MultiResource

    blob = factory.Sequence(_content_file)
    optional_blob = factory.Sequence(_content_file)
