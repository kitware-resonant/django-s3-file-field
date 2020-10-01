import pytest

from s3_file_field._multipart import (
    PartFinalizationRequest,
    PartInitializationResponse,
    UploadFinalizationRequest,
    UploadInitializationResponse,
)
from s3_file_field.views import (
    UploadFinalizationRequestSerializer,
    UploadInitializationRequestSerializer,
    UploadInitializationResponseSerializer,
)


@pytest.fixture
def initialization() -> UploadInitializationResponse:
    return UploadInitializationResponse(
        object_key='test-object-key',
        upload_id='test-upload-id',
        parts=[
            PartInitializationResponse(
                part_number=1,
                size=10_000,
                upload_url='http://minio.test/test-bucket/1',
            ),
            PartInitializationResponse(
                part_number=2,
                size=3_500,
                upload_url='http://minio.test/test-bucket/2',
            ),
        ],
    )


def test_upload_request_deserialization():
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


def test_upload_initialization_serialization(
    initialization: UploadInitializationResponse,
):
    serializer = UploadInitializationResponseSerializer(initialization)
    assert isinstance(serializer.data, dict)


def test_upload_finalization_deserialization():
    serializer = UploadFinalizationRequestSerializer(
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
    finalization = serializer.save()
    assert isinstance(finalization, UploadFinalizationRequest)
    assert all(isinstance(part, PartFinalizationRequest) for part in finalization.parts)
