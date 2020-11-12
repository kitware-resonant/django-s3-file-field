from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import math
from typing import Iterator, List, Tuple

from django.core.files.storage import Storage


@dataclass
class InitializedPart:
    part_number: int
    size: int
    upload_url: str


@dataclass
class InitializedUpload:
    object_key: str
    upload_id: str
    parts: List[InitializedPart]


@dataclass
class PartCompletion:
    part_number: int
    size: int
    etag: str


@dataclass
class UploadCompletion:
    object_key: str
    upload_id: str
    parts: List[PartCompletion]


@dataclass
class CompletedUpload:
    complete_url: str
    body: str


class UnsupportedStorageException(Exception):
    """Raised when MultipartManager does not support the given Storage."""

    pass


class MultipartManager:
    """A facade providing management of S3 multipart uploads to multiple Storages."""

    def initialize_upload(
        self, object_key: str, file_size: int, part_size: int = None
    ) -> InitializedUpload:
        upload_id = self._create_upload_id(object_key)
        parts = [
            InitializedPart(
                part_number=part_number,
                size=part_size,
                upload_url=self._generate_presigned_part_url(
                    object_key, upload_id, part_number, part_size
                ),
            )
            for part_number, part_size in self._iter_part_sizes(file_size, part_size)
        ]
        return InitializedUpload(object_key=object_key, upload_id=upload_id, parts=parts)

    def complete_upload(self, completion: UploadCompletion) -> CompletedUpload:
        complete_url = self._generate_presigned_complete_url(completion)
        body = self._generate_presigned_complete_body(completion)
        return CompletedUpload(complete_url=complete_url, body=body)

    def _generate_presigned_complete_body(self, completion: UploadCompletion) -> str:
        """
        Generate the body of a presigned completion request.

        See https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html
        """
        body = '<?xml version="1.0" encoding="UTF-8"?>'
        body += '<CompleteMultipartUpload xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        for part in completion.parts:
            body += '<Part>'
            body += f'<PartNumber>{part.part_number}</PartNumber>'
            body += f'<ETag>{part.etag}</ETag>'
            body += '</Part>'
        body += '</CompleteMultipartUpload>'
        return body

    def test_upload(self):
        object_key = '.s3-file-field-test-file'
        try:
            # TODO: is it possible to use a shorter timeout?
            upload_id = self._create_upload_id(object_key)
            self._abort_upload_id(object_key, upload_id)
        except Exception:
            # TODO: Capture and raise more specific exceptions, abstracted over the clients
            raise

    @classmethod
    def from_storage(cls, storage: Storage) -> MultipartManager:
        try:
            from storages.backends.s3boto3 import S3Boto3Storage
        except ImportError:
            pass
        else:
            if isinstance(storage, S3Boto3Storage):
                from ._multipart_boto3 import Boto3MultipartManager

                return Boto3MultipartManager(storage)

        try:
            from minio_storage.storage import MinioStorage
        except ImportError:
            pass
        else:
            if isinstance(storage, MinioStorage):
                from ._multipart_minio import MinioMultipartManager

                return MinioMultipartManager(storage)

        raise UnsupportedStorageException('Unsupported storage provider.')

    @classmethod
    def supported_storage(cls, storage: Storage) -> bool:
        try:
            cls.from_storage(storage)
        except UnsupportedStorageException:
            return False
        # Allow other exceptions to propagate
        else:
            return True

    # The AWS default expiration of 1 hour may not be enough for large uploads to complete
    _url_expiration = timedelta(hours=24)

    def _create_upload_id(self, object_key: str) -> str:
        raise NotImplementedError

    def _abort_upload_id(self, object_key: str, upload_id: str) -> None:
        raise NotImplementedError

    def _generate_presigned_part_url(
        self, object_key: str, upload_id: str, part_number: int, part_size: int
    ) -> str:
        raise NotImplementedError

    def _generate_presigned_complete_url(self, completion: UploadCompletion) -> str:
        raise NotImplementedError

    def get_object_size(self, object_key: str) -> int:
        raise NotImplementedError

    @staticmethod
    def _iter_part_sizes(file_size: int, part_size: int = None) -> Iterator[Tuple[int, int]]:
        if part_size is None:
            # 5 MB
            # TODO: pick a sane default; 1GB?
            part_size = 5 * 2 ** 20

        # S3 multipart limits: https://docs.aws.amazon.com/AmazonS3/latest/dev/qfacts.html

        if file_size > 5 * 2 ** 40:
            raise Exception('File is larger than the S3 maximum object size.')

        # 10k is the maximum number of allowed parts
        max_parts = 10_000
        if math.ceil(file_size / part_size) >= max_parts:
            part_size = math.ceil(file_size / max_parts)

        # 5MB is the minimum part size
        min_part_size = 5 * 2 ** 20
        if part_size < min_part_size:
            part_size = min_part_size

        # 5GB is the maximum part size
        max_part_size = 5 * 2 ** 30
        if part_size > max_part_size:
            part_size = max_part_size

        remaining_file_size = file_size
        part_num = 1
        while remaining_file_size > 0:
            current_part_size = (
                part_size if remaining_file_size - part_size > 0 else remaining_file_size
            )

            yield part_num, current_part_size

            part_num += 1
            remaining_file_size -= part_size

    # TODO: key name encoding...
