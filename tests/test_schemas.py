from __future__ import annotations

from pydantic import ValidationError
import pytest

from factories import FieldValueFactory, UploadTokenFactory
from s3_file_field._schemas import (
    CompletionRequest,
    FieldValue,
    FinalizationRequest,
    InitiationRequest,
)


def test_initiation_request_deserialization() -> None:
    InitiationRequest.model_validate(
        {
            "field": "test_app.Resource.blob",
            "file_name": "test-name.jpg",
            "file_size": 15,
            "content_type": "image/jpeg",
        }
    )


def test_initiation_request_file_size_within_max_size() -> None:
    InitiationRequest.model_validate(
        {
            "field": "test_app.LimitedResource.blob",
            "file_name": "test-name.jpg",
            "file_size": 10,
            "content_type": "image/jpeg",
        }
    )


def test_initiation_request_file_size_exceeds_max_size() -> None:
    with pytest.raises(ValidationError, match=r"file size exceeds the maximum of 10 bytes"):
        InitiationRequest.model_validate(
            {
                "field": "test_app.LimitedResource.blob",
                "file_name": "test-name.jpg",
                "file_size": 11,
                "content_type": "image/jpeg",
            }
        )


def test_completion_request_deserialization() -> None:
    upload_token = UploadTokenFactory.build()
    completion_request = CompletionRequest.model_validate(
        {
            "upload_token": upload_token,
            "parts": [
                {"part_number": 2, "etag": '"9a0364b9e99bb480dd25e1f0284c8555"'},
                {"part_number": 1, "etag": "79b16a42b3e022500b1d0723a4f6cbf3-2"},
            ],
        }
    )
    assert completion_request.parts[0].part_number == 1
    assert completion_request.parts[1].part_number == 2


def test_finalization_request_deserialization() -> None:
    upload_token = UploadTokenFactory.build()
    FinalizationRequest.model_validate(
        {
            "upload_token": upload_token,
        }
    )


def test_completion_request_parts_duplicate() -> None:
    upload_token = UploadTokenFactory.build()
    with pytest.raises(ValidationError, match=r"duplicate part numbers"):
        CompletionRequest.model_validate(
            {
                "upload_token": upload_token,
                "parts": [
                    {"part_number": 1, "etag": '"9a0364b9e99bb480dd25e1f0284c8555"'},
                    {"part_number": 1, "etag": '"79b16a42b3e022500b1d0723a4f6cbf3"'},
                ],
            }
        )


def test_field_value_deserialization() -> None:
    """A signed FieldValue round-trips through its serialized form."""
    field_value = FieldValueFactory.build()

    assert FieldValue.model_validate(field_value.model_dump()) == field_value
