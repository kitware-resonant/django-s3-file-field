from __future__ import annotations

from django.core import signing
import pytest
from rest_framework.exceptions import ValidationError

from s3_file_field._multipart import TransferredPart, TransferredParts
from s3_file_field.views import (
    FinalizationRequest,
    FinalizationRequestSerializer,
    UploadCompletionRequestSerializer,
    UploadInitializationRequest,
    UploadInitializationRequestSerializer,
)


def test_upload_initialization_request_deserialization() -> None:
    serializer = UploadInitializationRequestSerializer(
        data={
            "field_id": "test_app.Resource.blob",
            "file_name": "test-name.jpg",
            "file_size": 15,
            "content_type": "image/jpeg",
        }
    )
    assert serializer.is_valid(raise_exception=True)
    request = serializer.save()
    assert isinstance(request, UploadInitializationRequest)


def test_upload_initialization_request_deserialization_file_id_invalid() -> None:
    serializer = UploadInitializationRequestSerializer(
        data={
            "field_id": "bad.id",
            "file_name": "test-name.jpg",
            "file_size": 15,
            "content_type": "image/jpeg",
        }
    )
    with pytest.raises(ValidationError) as e:
        serializer.is_valid(raise_exception=True)
    assert e.value.detail == {"field_id": ['Invalid field ID: "bad.id".']}


def test_upload_completion_request_deserialization() -> None:
    upload_signature = signing.dumps({"object_key": "test-object-key", "field_id": "test-field-id"})
    serializer = UploadCompletionRequestSerializer(
        data={
            "upload_signature": upload_signature,
            "upload_id": "test-upload-id",
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
