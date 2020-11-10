import pytest

from s3_file_field._multipart import (
    InitializedPart,
    InitializedUpload,
    PartCompletion,
    UploadCompletion,
)
from s3_file_field.views import (
    UploadCompletionRequestSerializer,
    UploadInitializationRequestSerializer,
    UploadInitializationResponseSerializer,
)


@pytest.fixture
def initialization() -> InitializedUpload:
    return InitializedUpload(
        object_key='test-object-key',
        upload_id='test-upload-id',
        parts=[
            InitializedPart(
                part_number=1,
                size=10_000,
                upload_url='http://minio.test/test-bucket/1',
            ),
            InitializedPart(
                part_number=2,
                size=3_500,
                upload_url='http://minio.test/test-bucket/2',
            ),
        ],
    )


def test_upload_initialization_request_deserialization():
    serializer = UploadInitializationRequestSerializer(
        data={
            'field_id': 'package.Class.field',
            'file_name': 'test-name.jpg',
            'file_size': 15,
        }
    )
    assert serializer.is_valid(raise_exception=True)
    request = serializer.validated_data
    assert isinstance(request, dict)


def test_upload_initialization_response_serialization(
    initialization: InitializedUpload,
):
    serializer = UploadInitializationResponseSerializer(initialization)
    assert isinstance(serializer.data, dict)


def test_upload_completion_request_deserialization():
    serializer = UploadCompletionRequestSerializer(
        data={
            'field_id': 'package.Class.field',
            'object_key': 'test-object-key',
            'upload_id': 'test-upload-id',
            'parts': [
                {'part_number': 1, 'size': 10_000, 'etag': 'test-etag-1'},
                {'part_number': 2, 'size': 3_500, 'etag': 'test-etag-2'},
            ],
        }
    )

    assert serializer.is_valid(raise_exception=True)
    completion = serializer.save()
    assert isinstance(completion, UploadCompletion)
    assert all(isinstance(part, PartCompletion) for part in completion.parts)
