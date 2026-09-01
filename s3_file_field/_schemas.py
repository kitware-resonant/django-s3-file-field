from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, StringConstraints

from ._pydantic_utils import MimeType, S3FileFieldId, SignedModel


class UploadInitializationRequestModel(BaseModel):
    field_id: S3FileFieldId
    file_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    file_size: Annotated[int, Field(gt=0)]
    content_type: MimeType


class UploadSignatureModel(SignedModel):
    field_id: S3FileFieldId
    object_key: str


class PartInitializationModel(BaseModel):
    part_number: Annotated[int, Field(ge=1)]
    size: Annotated[int, Field(gt=0)]
    upload_url: HttpUrl


class UploadInitializationResponseModel(BaseModel):
    upload_id: str
    parts: Annotated[list[PartInitializationModel], Field(min_length=1)]
    upload_signature: UploadSignatureModel
