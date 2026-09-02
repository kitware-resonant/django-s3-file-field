from __future__ import annotations

from pydantic import ValidationError
import pytest

from s3_file_field._schemas import (
    CompletionRequest,
    FinalizationRequest,
    InitiationRequest,
    UploadToken,
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


def test_completion_request_deserialization(upload_token: UploadToken) -> None:
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


def test_finalization_request_deserialization(upload_token: UploadToken) -> None:
    FinalizationRequest.model_validate(
        {
            "upload_token": upload_token,
        }
    )


def test_completion_request_parts_duplicate(upload_token: UploadToken) -> None:
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
