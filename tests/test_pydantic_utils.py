from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from django.core.signing import TimestampSigner
import factory
from freezegun import freeze_time
from pydantic import BaseModel, TypeAdapter, ValidationError
import pytest

from s3_file_field._pydantic_utils import MimeType, S3FileFieldId, SignedModel
from test_app.models import Resource

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from s3_file_field.fields import S3FileField


class ExampleSignedModel(SignedModel):
    name: str
    when: datetime


class ExampleEnvelopeModel(BaseModel):
    signature: ExampleSignedModel


class ExampleSignedModelFactory(factory.Factory[ExampleSignedModel]):
    class Meta:
        model = ExampleSignedModel

    name = "test-name"
    when = datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)

    @classmethod
    def _build(
        cls, model_class: type[ExampleSignedModel], *args: Any, **kwargs: Any
    ) -> ExampleSignedModel:
        # SignedModel field values cannot be passed directly to __init__, as its wrap
        # validator would attempt to unsign them; use model_construct, as the library does.
        return model_class.model_construct(*args, **kwargs)


def test_signed_model_round_trip() -> None:
    model = ExampleSignedModelFactory.build()

    signed = model.model_dump()
    assert isinstance(signed, str)

    assert ExampleSignedModel.model_validate(signed) == model


def test_signed_model_tampered() -> None:
    signed = cast("str", ExampleSignedModelFactory.build().model_dump())
    tampered = signed[:-1] + ("A" if signed[-1] != "A" else "B")

    with pytest.raises(ValidationError, match=r"invalid signature"):
        ExampleSignedModel.model_validate(tampered)


def test_signed_model_salt_mismatch(mocker: MockerFixture) -> None:
    mocker.patch.object(ExampleSignedModel, "signer", TimestampSigner(salt="other-salt"))
    signed = ExampleSignedModelFactory.build().model_dump()
    mocker.stopall()

    with pytest.raises(ValidationError, match=r"invalid signature"):
        ExampleSignedModel.model_validate(signed)


def test_signed_model_expired() -> None:
    # Sign at a fixed date, longer than "max_age" ago
    with freeze_time("2020-01-01"):
        signed = ExampleSignedModelFactory.build().model_dump()

    with pytest.raises(ValidationError, match=r"invalid signature"):
        ExampleSignedModel.model_validate(signed)


def test_signed_model_nested() -> None:
    envelope = ExampleEnvelopeModel(signature=ExampleSignedModelFactory.build())

    dumped = envelope.model_dump()
    assert isinstance(dumped["signature"], str)

    assert ExampleEnvelopeModel.model_validate(dumped) == envelope


S3_FILE_FIELD_ID_ADAPTER: TypeAdapter[S3FileField] = TypeAdapter(S3FileFieldId)


def test_s3_file_field_id_round_trip() -> None:
    field = Resource._meta.get_field("blob")

    field_id = S3_FILE_FIELD_ID_ADAPTER.dump_python(field)
    assert field_id == "test_app.Resource.blob"

    assert S3_FILE_FIELD_ID_ADAPTER.validate_python(field_id) is field


def test_s3_file_field_id_unknown() -> None:
    with pytest.raises(ValidationError, match=r"unknown S3FileField instance"):
        S3_FILE_FIELD_ID_ADAPTER.validate_python("bad.id")


def test_s3_file_field_id_type_invalid() -> None:
    with pytest.raises(ValidationError, match=r"expected string"):
        S3_FILE_FIELD_ID_ADAPTER.validate_python(42)


MIME_TYPE_ADAPTER: TypeAdapter[str] = TypeAdapter(MimeType)


@pytest.mark.parametrize(
    "mime_type",
    [
        "text/plain",
        "application/octet-stream",
        "application/vnd.api+json",
        "text/plain; charset=utf-8",
        "text/plain;charset=utf-8",
        'text/plain; title="ab cd"',
        "text/plain; charset",
    ],
    ids=[
        "plain",
        "octet-stream",
        "suffix",
        "parameter",
        "unspaced-parameter",
        "quoted-parameter",
        "lenient-parameter",
    ],
)
def test_mime_type_valid(mime_type: str) -> None:
    MIME_TYPE_ADAPTER.validate_python(mime_type)


@pytest.mark.parametrize(
    "mime_type",
    [
        "",
        "text",
        "text/",
        "/plain",
        "text plain",
        "text/pläin",
        "text/plain\r\nx-amz-meta-evil: 1",
        "text/" + "a" * 251,
    ],
    ids=[
        "empty",
        "no-slash",
        "no-subtype",
        "no-type",
        "space",
        "non-ascii",
        "crlf-injection",
        "too-long",
    ],
)
def test_mime_type_invalid(mime_type: str) -> None:
    with pytest.raises(ValidationError):
        MIME_TYPE_ADAPTER.validate_python(mime_type)


@pytest.mark.parametrize(
    "mime_type",
    [" text/plain", "text/plain ", "text/plain\n"],
    ids=["leading-space", "trailing-space", "trailing-newline"],
)
def test_mime_type_whitespace(mime_type: str) -> None:
    assert MIME_TYPE_ADAPTER.validate_python(mime_type) == "text/plain"
