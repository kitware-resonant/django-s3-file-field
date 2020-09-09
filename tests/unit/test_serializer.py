import pytest

from s3_file_field._multipart import (
    MultipartFinalization,
    MultipartInitialization,
    PartFinalization,
    PartInitialization,
)
from s3_file_field.views import MultipartFinalizationSerializer, MultipartInitializationSerializer


@pytest.fixture
def multipart_initialization() -> MultipartInitialization:
    return MultipartInitialization(
        object_key='test-object-key',
        upload_id='test-upload-id',
        parts=[
            PartInitialization(
                part_number=1,
                size=10_000,
                upload_url='http://minio.test/test-bucket/1',
            ),
            PartInitialization(
                part_number=2,
                size=3_500,
                upload_url='http://minio.test/test-bucket/2',
            ),
        ],
    )


def test_multipart_initialization_serialization(
    multipart_initialization: MultipartInitialization,
):
    serializer = MultipartInitializationSerializer(multipart_initialization)
    assert isinstance(serializer.data, dict)


def test_multipart_finalization_deserialization():
    serializer = MultipartFinalizationSerializer(
        data={
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
    assert isinstance(finalization, MultipartFinalization)
    assert all(isinstance(part, PartFinalization) for part in finalization.parts)
