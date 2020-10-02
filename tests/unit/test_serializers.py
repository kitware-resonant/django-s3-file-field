import pytest

from s3_file_field._multipart import (
    InitializedPart,
    InitializedUpload,
    PartFinalization,
    UploadFinalization,
)
from s3_file_field.views import (
    UploadFinalizationRequestSerializer,
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
    initialization: InitializedUpload,
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
    assert isinstance(finalization, UploadFinalization)
    assert all(isinstance(part, PartFinalization) for part in finalization.parts)
