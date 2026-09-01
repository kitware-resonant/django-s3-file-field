from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from ._pydantic_utils import (
    ETag,
    MimeType,
    S3FileFieldId,
    SignedModel,
    VerbatimUrl,
)


class UploadInitializationRequestModel(BaseModel, frozen=True, extra="forbid"):
    field_id: S3FileFieldId
    file_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    file_size: Annotated[int, Field(gt=0)]
    content_type: MimeType


class UploadSignatureModel(SignedModel, frozen=True, extra="forbid"):
    field_id: S3FileFieldId
    upload_id: str
    object_key: str


class PartInitializationModel(BaseModel, frozen=True, extra="forbid"):
    part_number: Annotated[int, Field(ge=1)]
    size: Annotated[int, Field(gt=0)]
    upload_url: VerbatimUrl


class UploadInitializationResponseModel(BaseModel, frozen=True, extra="forbid"):
    upload_signature: UploadSignatureModel
    parts: Annotated[list[PartInitializationModel], Field(min_length=1)]


class PartCompletionModel(BaseModel, frozen=True, extra="forbid"):
    part_number: Annotated[int, Field(ge=1)]
    # This is interpolated into the completion request's XML body, so it must never
    # admit XML metacharacters.
    etag: ETag


class UploadCompletionRequestModel(BaseModel, frozen=True, extra="forbid"):
    upload_signature: UploadSignatureModel
    parts: Annotated[list[PartCompletionModel], Field(min_length=1)]

    @field_validator("parts", mode="after")
    @classmethod
    def ordered_parts(cls, value: list[PartCompletionModel]) -> list[PartCompletionModel]:
        return sorted(value, key=lambda part: part.part_number)


class UploadCompletionResponseModel(BaseModel, frozen=True, extra="forbid"):
    complete_url: VerbatimUrl
    body: str


class FieldValueModel(SignedModel, frozen=True, extra="forbid"):
    object_key: str
    file_size: Annotated[int, Field(gt=0)]


class UploadFinalizationRequestModel(BaseModel, frozen=True, extra="forbid"):
    upload_signature: UploadSignatureModel


class UploadFinalizationResponseModel(BaseModel, frozen=True, extra="forbid"):
    field_value: FieldValueModel
