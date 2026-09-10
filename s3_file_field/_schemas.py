from __future__ import annotations

from typing import Annotated, Self

from django.core.signing import TimestampSigner
from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from ._pydantic_utils import (
    ETag,
    MimeType,
    S3FileFieldRef,
    SignedModel,
    VerbatimUrl,
)


class InitiationRequest(BaseModel, frozen=True, extra="forbid"):
    field: S3FileFieldRef
    file_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    file_size: Annotated[int, Field(gt=0)]
    content_type: MimeType

    # This needs access to multiple fields
    @model_validator(mode="after")
    def max_file_size(self) -> Self:
        if self.file_size > self.field.effective_max_size:
            raise ValueError(
                f"file size exceeds the maximum of {self.field.effective_max_size} bytes"
            )
        return self


class UploadToken(SignedModel, frozen=True, extra="forbid"):
    signer = TimestampSigner(salt="s3_file_field.UploadToken")

    field: S3FileFieldRef
    upload_id: str
    object_key: str


class PresignedPart(BaseModel, frozen=True, extra="forbid"):
    part_number: Annotated[int, Field(ge=1)]
    size: Annotated[int, Field(gt=0)]
    url: VerbatimUrl


class InitiationResponse(BaseModel, frozen=True, extra="forbid"):
    upload_token: UploadToken
    parts: Annotated[list[PresignedPart], Field(min_length=1)]


class CompletedPart(BaseModel, frozen=True, extra="forbid"):
    part_number: Annotated[int, Field(ge=1)]
    # This is interpolated into the completion request's XML body, so it must never
    # admit XML metacharacters.
    etag: ETag


class CompletionRequest(BaseModel, frozen=True, extra="forbid"):
    upload_token: UploadToken
    parts: Annotated[list[CompletedPart], Field(min_length=1)]

    @field_validator("parts", mode="after")
    @classmethod
    def ordered_parts(cls, value: list[CompletedPart]) -> list[CompletedPart]:
        return sorted(value, key=lambda part: part.part_number)

    @field_validator("parts", mode="after")
    @classmethod
    def unique_parts(cls, value: list[CompletedPart]) -> list[CompletedPart]:
        part_numbers = [part.part_number for part in value]
        if len(part_numbers) != len(set(part_numbers)):
            raise ValueError("duplicate part numbers")
        return value


class CompletionResponse(BaseModel, frozen=True, extra="forbid"):
    url: VerbatimUrl
    body: str


class FieldValue(SignedModel, frozen=True, extra="forbid"):
    signer = TimestampSigner(salt="s3_file_field.FieldValue")

    field: S3FileFieldRef
    object_key: str
    file_size: Annotated[int, Field(gt=0)]


class FinalizationRequest(BaseModel, frozen=True, extra="forbid"):
    upload_token: UploadToken


class FinalizationResponse(BaseModel, frozen=True, extra="forbid"):
    field_value: FieldValue
