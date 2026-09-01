from __future__ import annotations

from django.core import signing

from s3_file_field._multipart import TransferredPart, TransferredParts
from s3_file_field.views import (
    FinalizationRequest,
    FinalizationRequestSerializer,
    UploadCompletionRequestSerializer,
)


def test_upload_completion_request_deserialization() -> None:
    upload_signature = signing.dumps(
        {
            "field_id": "test-field-id",
            "upload_id": "test-upload-id",
            "object_key": "test-object-key",
        },
        salt="s3_file_field",
    )
    serializer = UploadCompletionRequestSerializer(
        data={
            "upload_signature": upload_signature,
            "parts": [
                {"part_number": 1, "size": 10_000, "etag": "test-etag-1"},
                {"part_number": 2, "size": 3_500, "etag": "test-etag-2"},
            ],
        }
    )

    assert serializer.is_valid(raise_exception=True)
    completion = serializer.save()
    assert isinstance(completion, TransferredParts)
    assert all(isinstance(part, TransferredPart) for part in completion.parts)


def test_finalization_request_deserialization() -> None:
    upload_signature = signing.dumps({"object_key": "test-object-key", "field_id": "test-field-id"})
    serializer = FinalizationRequestSerializer(
        data={
            "upload_signature": upload_signature,
        }
    )

    assert serializer.is_valid(raise_exception=True)
    finalization_request = serializer.save()
    assert isinstance(finalization_request, FinalizationRequest)
