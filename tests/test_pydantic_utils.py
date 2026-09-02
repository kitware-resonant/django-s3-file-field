from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from django.core.signing import TimestampSigner
from freezegun import freeze_time
from pydantic import BaseModel, TypeAdapter, ValidationError
import pytest

from conftest import SignedModelFactory
from s3_file_field._pydantic_utils import (
    ETag,
    MimeType,
    S3FileFieldRef,
    SignedModel,
    VerbatimUrl,
)
from test_app.models import Resource

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from s3_file_field.fields import S3FileField


class ExampleSignedModel(SignedModel, frozen=True, extra="forbid"):
    signer = TimestampSigner(salt="test.ExampleSignedModel")

    name: str
    when: datetime


class ExampleEnvelopeModel(BaseModel, frozen=True, extra="forbid"):
    signature: ExampleSignedModel


class ExampleSignedModelFactory(SignedModelFactory[ExampleSignedModel]):
    class Meta:
        model = ExampleSignedModel

    name = "test-name"
    when = datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)


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


@pytest.mark.parametrize(
    "data",
    [42, None, b"abc", {"name": "test-name"}],
    ids=["int", "none", "bytes", "dict"],
)
def test_signed_model_type_invalid(data: object) -> None:
    with pytest.raises(ValidationError, match=r"expected string"):
        ExampleSignedModel.model_validate(data)


def test_signed_model_nested() -> None:
    envelope = ExampleEnvelopeModel(signature=ExampleSignedModelFactory.build())

    dumped = envelope.model_dump()
    assert isinstance(dumped["signature"], str)

    assert ExampleEnvelopeModel.model_validate(dumped) == envelope


S3_FILE_FIELD_REF_ADAPTER: TypeAdapter[S3FileField] = TypeAdapter(S3FileFieldRef)


def test_s3_file_field_ref_round_trip() -> None:
    field = Resource._meta.get_field("blob")

    field_id = S3_FILE_FIELD_REF_ADAPTER.dump_python(field)
    assert field_id == "test_app.Resource.blob"

    assert S3_FILE_FIELD_REF_ADAPTER.validate_python(field_id) is field


def test_s3_file_field_ref_unknown() -> None:
    with pytest.raises(ValidationError, match=r"unknown S3FileField instance"):
        S3_FILE_FIELD_REF_ADAPTER.validate_python("bad.id")


def test_s3_file_field_ref_type_invalid() -> None:
    with pytest.raises(ValidationError, match=r"expected string"):
        S3_FILE_FIELD_REF_ADAPTER.validate_python(42)


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


VERBATIM_URL_ADAPTER: TypeAdapter[str] = TypeAdapter(VerbatimUrl)


def test_verbatim_url_valid() -> None:
    # Presigned URLs must round-trip byte-exact, with no normalization
    url = "https://bucket.example.com:9000/key%2Fname?X-Amz-Signature=aBc123&x=%20"
    assert VERBATIM_URL_ADAPTER.validate_python(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/key",
        "https://example.com/a b",
        "https://example.com/a\nb",
    ],
    ids=["scheme", "space", "newline"],
)
def test_verbatim_url_invalid(url: str) -> None:
    with pytest.raises(ValidationError):
        VERBATIM_URL_ADAPTER.validate_python(url)


ETAG_ADAPTER: TypeAdapter[str] = TypeAdapter(ETag)


@pytest.mark.parametrize(
    "etag",
    [
        "9a0364b9e99bb480dd25e1f0284c8555",
        '"9a0364b9e99bb480dd25e1f0284c8555"',
        "9A0364B9E99BB480DD25E1F0284C8555",
        "79b16a42b3e022500b1d0723a4f6cbf3-2",
        '"79b16a42b3e022500b1d0723a4f6cbf3-1000"',
    ],
    ids=["bare", "quoted", "uppercase", "multipart", "quoted-multipart"],
)
def test_etag_valid(etag: str) -> None:
    ETAG_ADAPTER.validate_python(etag)


@pytest.mark.parametrize(
    "etag",
    [
        "",
        "9a0364b9e99bb480dd25e1f0284c855",
        "9a0364b9e99bb480dd25e1f0284c85555",
        "9a0364b9e99bb480dd25e1f0284c855g",
        '"9a0364b9e99bb480dd25e1f0284c8555',
        '9a0364b9e99bb480dd25e1f0284c8555"',
        "9a0364b9e99bb480dd25e1f0284c8555-",
        "9a0364b9e99bb480dd25e1f0284c8555</ETag><Evil>",
        "9a0364b9e99bb480dd25e1f0284c8555&lt;",
    ],
    ids=[
        "empty",
        "too-short",
        "too-long",
        "non-hex",
        "unbalanced-leading-quote",
        "unbalanced-trailing-quote",
        "empty-part-count",
        "xml-tag-injection",
        "xml-entity-injection",
    ],
)
def test_etag_invalid(etag: str) -> None:
    with pytest.raises(ValidationError):
        ETAG_ADAPTER.validate_python(etag)
