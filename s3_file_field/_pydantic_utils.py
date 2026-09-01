from __future__ import annotations

from datetime import timedelta
import json
from typing import Annotated, Any, ClassVar, Self

from django.core.signing import BadSignature, TimestampSigner
from pydantic import (
    BaseModel,
    ModelWrapValidatorHandler,
    PlainSerializer,
    PlainValidator,
    SerializerFunctionWrapHandler,
    StringConstraints,
    model_serializer,
    model_validator,
)
from pydantic_core import PydanticSerializationError, from_json, to_json, to_jsonable_python

from ._registry import get_field
from .fields import S3FileField


class _PydanticSerializer:
    """
    A JSON serializer for `django.core.signing` which uses Pydantic to do its work.

    Unlike `django.core.signing.JSONSerializer`, this supports serializing any type
    which Pydantic can convert to JSON (datetimes, UUIDs, etc.).
    """

    def dumps(self, obj: Any) -> bytes:
        return to_json(obj)

    def loads(self, data: bytes) -> Any:
        return from_json(data)


class PydanticEncoder(json.JSONEncoder):
    """A JSON encoder which uses Pydantic to encode types the `json` module cannot."""

    def default(self, o: Any) -> Any:
        try:
            return to_jsonable_python(o)
        except PydanticSerializationError:
            # Raises a TypeError, per the JSONEncoder spec
            return super().default(o)


class SignedModel(BaseModel):
    """
    A base class for Pydantic models which serialize to a cryptographically signed string.

    Serializing (e.g. with `model_dump`) produces a single opaque string, containing the
    model's fields plus a timestamped signature. Validating (e.g. with `model_validate`)
    accepts such a string, raising a `ValidationError` if the signature is invalid or
    is older than `max_age`; an already-constructed instance is passed through unchanged.
    """

    signer: ClassVar[TimestampSigner] = TimestampSigner(salt="s3_file_field")
    max_age: ClassVar[timedelta] = timedelta(days=1)

    @model_validator(mode="wrap")
    @classmethod
    def _validate_model(cls, data: Any, handler: ModelWrapValidatorHandler[Self]) -> Self:
        if isinstance(data, cls):
            return data
        try:
            serialized_data = cls.signer.unsign_object(
                data, serializer=_PydanticSerializer, max_age=cls.max_age
            )
        except BadSignature as e:
            raise ValueError(f"invalid signature on {cls.__name__}: {e}") from e
        return handler(serialized_data)

    @model_serializer(mode="wrap")
    def _serialize_model(self, handler: SerializerFunctionWrapHandler) -> str:
        serialized_data = handler(self)
        return self.signer.sign_object(serialized_data, serializer=_PydanticSerializer)


def _validate_s3_file_field_ref(value: Any) -> S3FileField:
    if isinstance(value, S3FileField):
        return value
    if isinstance(value, str):
        try:
            return get_field(value)
        except KeyError:
            # Chaining the KeyError doesn't add any info
            raise ValueError(f"unknown S3FileField instance: {value!r}") from None
    raise ValueError(f"expected string, got {type(value).__name__}")


def _serialize_s3_file_field_ref(value: S3FileField) -> str:
    return value.id


S3FileFieldId = Annotated[
    S3FileField,
    PlainValidator(_validate_s3_file_field_ref, json_schema_input_type=str),
    PlainSerializer(_serialize_s3_file_field_ref),
]


# This value becomes the object's "Content-Type" HTTP header on S3, so to prevent header
# injection, allow only printable US-ASCII in a "type/subtype[; parameters]" shape. This
# is deliberately looser than the RFC 9110 grammar, accepting ordinary real-world media
# types.
MimeType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        max_length=255,
        pattern=r"^[A-Za-z0-9._+-]+/[A-Za-z0-9._+-]+(?:;[ -~]*)?$",
    ),
]
