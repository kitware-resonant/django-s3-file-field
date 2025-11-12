from django.core import signing
import pytest
from rest_framework.exceptions import ValidationError

from s3_file_field._multipart import (
    PresignedPartTransfer,
    PresignedTransfer,
    TransferredPart,
    TransferredParts,
)
from s3_file_field.views import (
    UploadCompletionRequestSerializer,
    UploadInitializationRequestSerializer,
    UploadInitializationResponseSerializer,
)


@pytest.fixture()
def initialization() -> PresignedTransfer:
    return PresignedTransfer(
        object_key="test-object-key",
        upload_id="test-upload-id",
        parts=[
            PresignedPartTransfer(
                part_number=1,
                size=10_000,
                upload_url="http://minio.test/test-bucket/1",
            ),
            PresignedPartTransfer(
                part_number=2,
                size=3_500,
                upload_url="http://minio.test/test-bucket/2",
            ),
        ],
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
    request = serializer.validated_data
    assert isinstance(request, dict)


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


def test_upload_initialization_response_serialization(
    initialization: PresignedTransfer,
) -> None:
    serializer = UploadInitializationResponseSerializer(
        {
            "object_key": initialization.object_key,
            "upload_id": initialization.upload_id,
            "acl": "",
            "parts": initialization.parts,
            "upload_signature": "test-upload-signature",
        }
    )
    assert isinstance(serializer.data, dict)


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
