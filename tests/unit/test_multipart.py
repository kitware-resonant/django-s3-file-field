from django.core.files.storage import FileSystemStorage, Storage
from minio_storage.storage import MinioStorage
import pytest
import requests
from storages.backends.s3boto3 import S3Boto3Storage

from s3_file_field._multipart import MultipartManager, PartFinalization, UploadFinalization
from s3_file_field._multipart_boto3 import Boto3MultipartManager
from s3_file_field._multipart_minio import MinioMultipartManager


def mb(bytes_size: int) -> int:
    return bytes_size * 2 ** 20


def gb(bytes_size: int) -> int:
    return bytes_size * 2 ** 30


@pytest.fixture
def boto3_multipart_manager(s3boto3_storage: S3Boto3Storage) -> Boto3MultipartManager:
    return Boto3MultipartManager(s3boto3_storage)


@pytest.fixture
def minio_multipart_manager(minio_storage: MinioStorage) -> MinioMultipartManager:
    return MinioMultipartManager(minio_storage)


@pytest.fixture
def multipart_manager(storage: Storage) -> MultipartManager:
    return MultipartManager.from_storage(storage)


def test_multipart_manager_supported_storage(storage: Storage):
    assert MultipartManager.supported_storage(storage)


def test_multipart_manager_supported_storage_unsupported():
    storage = FileSystemStorage()
    assert not MultipartManager.supported_storage(storage)


def test_multipart_manager_initialize_upload(multipart_manager: MultipartManager):
    initialization = multipart_manager.initialize_upload(
        'new-object',
        100,
    )

    assert initialization


@pytest.mark.parametrize('file_size', [10, mb(10), mb(12)], ids=['10B', '10MB', '12MB'])
def test_multipart_manager_finalize_upload(multipart_manager: MultipartManager, file_size: int):
    initialization = multipart_manager.initialize_upload(
        'new-object',
        file_size,
    )

    finalization = UploadFinalization(
        object_key=initialization.object_key, upload_id=initialization.upload_id, parts=[]
    )

    for part in initialization.parts:
        resp = requests.put(part.upload_url, data=b'a' * part.size)
        resp.raise_for_status()
        finalization.parts.append(
            PartFinalization(
                part_number=part.part_number, size=part.size, etag=resp.headers['ETag']
            )
        )

    multipart_manager.finalize_upload(finalization)


def test_multipart_manager_test_upload(multipart_manager: MultipartManager):
    multipart_manager.test_upload()


def test_multipart_manager_create_upload_id(multipart_manager: MultipartManager):
    upload_id = multipart_manager._create_upload_id('new-object')
    assert isinstance(upload_id, str)


def test_multipart_manager_generate_presigned_part_url(multipart_manager: MultipartManager):
    upload_url = multipart_manager._generate_presigned_part_url(
        'new-object', 'fake-upload-id', 1, 100
    )

    assert isinstance(upload_url, str)


@pytest.mark.skip
def test_multipart_manager_generate_presigned_part_url_content_length(
    multipart_manager: MultipartManager,
):
    # TODO: make this work for Minio
    upload_url = multipart_manager._generate_presigned_part_url(
        'new-object', 'fake-upload-id', 1, 100
    )
    # Ensure Content-Length is a signed header
    assert 'content-length' in upload_url


@pytest.mark.parametrize(
    'file_size,requested_part_size,initial_part_size,final_part_size,part_count',
    [
        # Base
        (mb(50), mb(10), mb(10), mb(10), 5),
        # Different final size
        (mb(55), mb(10), mb(10), mb(5), 6),
        # Single part
        (mb(10), mb(10), 0, mb(10), 1),
        # Too small requested_part_size
        (mb(50), mb(2), mb(5), mb(5), 10),
        # Too large requested_part_size
        (gb(50), gb(10), gb(5), gb(5), 10),
        # Too many parts
        (mb(100_000), mb(5), mb(10), mb(10), 10_000),
        # TODO: file too large
    ],
    ids=[
        'base',
        'different_final',
        'single_part',
        'too_small_part',
        'too_large_part',
        'too_many_part',
    ],
)
def test_multipart_manager_iter_part_sizes(
    file_size, requested_part_size, initial_part_size, final_part_size, part_count
):
    part_nums, part_sizes = zip(*MultipartManager._iter_part_sizes(file_size, requested_part_size))

    # TOOD: zip(*) returns a tuple, but semantically this should be a list
    assert part_nums == tuple(range(1, part_count + 1))

    assert all(part_size == initial_part_size for part_size in part_sizes[:-1])
    assert part_sizes[-1] == final_part_size
