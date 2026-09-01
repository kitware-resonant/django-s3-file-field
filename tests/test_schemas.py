from __future__ import annotations

from s3_file_field._schemas import (
    UploadCompletionRequestModel,
    UploadFinalizationRequestModel,
    UploadInitializationRequestModel,
    UploadSignatureModel,
)


def test_upload_initialization_request_deserialization() -> None:
    UploadInitializationRequestModel.model_validate(
        {
            "field_id": "test_app.Resource.blob",
            "file_name": "test-name.jpg",
            "file_size": 15,
            "content_type": "image/jpeg",
        }
    )


def test_upload_completion_request_deserialization(upload_signature: UploadSignatureModel) -> None:
    completion_request = UploadCompletionRequestModel.model_validate(
        {
            "upload_signature": upload_signature,
            "parts": [
                {"part_number": 2, "etag": '"9a0364b9e99bb480dd25e1f0284c8555"'},
                {"part_number": 1, "etag": "79b16a42b3e022500b1d0723a4f6cbf3-2"},
            ],
        }
    )
    assert completion_request.parts[0].part_number == 1
    assert completion_request.parts[1].part_number == 2


def test_upload_finalization_request_deserialization(
    upload_signature: UploadSignatureModel,
) -> None:
    UploadFinalizationRequestModel.model_validate(
        {
            "upload_signature": upload_signature,
        }
    )
