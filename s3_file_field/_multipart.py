from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
import math
from typing import TYPE_CHECKING, Any, ClassVar

from s3_file_field._sizes import gb, mb

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.core.files.storage import Storage


@dataclass(frozen=True)
class PresignedPart:
    part_number: int
    size: int
    url: str


@dataclass(frozen=True)
class PresignedUpload:
    upload_id: str
    object_key: str
    parts: list[PresignedPart]


@dataclass(frozen=True)
class CompletedPart:
    part_number: int
    etag: str


@dataclass(frozen=True)
class PresignedCompletion:
    url: str
    body: str


class UnsupportedStorageError(Exception):
    """Raised when MultipartManager does not support the given Storage."""

    def __init__(self, *args: Any) -> None:
        super().__init__("Unsupported storage provider.", *args)


class ObjectNotFoundError(Exception):
    """Raised when an object cannot be found in the object store."""


class UploadTooLargeError(Exception):
    """Raised when an upload exceeds the maximum upload size for a Storage."""

    def __init__(self, *args: Any) -> None:
        super().__init__("File is larger than the maximum upload size.", *args)


class MultipartManager(ABC):
    """A facade providing management of S3 multipart uploads to multiple Storages."""

    baseline_part_size: ClassVar[int] = mb(64)
    max_object_size: ClassVar[int]
    # S3 multipart limits, also enforced by MinIO:
    # https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html
    max_parts: ClassVar[int] = 10_000
    min_part_size: ClassVar[int] = mb(5)
    max_part_size: ClassVar[int] = gb(5)

    @property
    def max_upload_size(self) -> int:
        return min(self.max_object_size, self.max_parts * self.max_part_size)

    def initiate_upload(
        self,
        object_key: str,
        file_size: int,
        content_type: str,
    ) -> PresignedUpload:
        if file_size > self.max_upload_size:
            raise UploadTooLargeError

        upload_id = self._create_upload_id(
            object_key,
            content_type,
        )
        parts = [
            PresignedPart(
                part_number=part_number,
                size=part_size,
                url=self._generate_presigned_part_url(
                    upload_id, object_key, part_number, part_size
                ),
            )
            for part_number, part_size in self._iter_part_sizes(file_size)
        ]
        return PresignedUpload(upload_id=upload_id, object_key=object_key, parts=parts)

    def complete_upload(
        self, upload_id: str, object_key: str, parts: list[CompletedPart]
    ) -> PresignedCompletion:
        url = self._generate_presigned_complete_url(upload_id, object_key)
        body = self._generate_presigned_complete_body(parts)
        return PresignedCompletion(url=url, body=body)

    def _generate_presigned_complete_body(self, parts: list[CompletedPart]) -> str:
        """
        Generate the body of a presigned completion request.

        See https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html
        """
        body = '<?xml version="1.0" encoding="UTF-8"?>'
        body += '<CompleteMultipartUpload xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        for part in parts:
            body += "<Part>"
            body += f"<PartNumber>{part.part_number}</PartNumber>"
            body += f"<ETag>{part.etag}</ETag>"
            body += "</Part>"
        body += "</CompleteMultipartUpload>"
        return body

    def test_upload(self) -> None:
        object_key = ".s3-file-field-test-file"
        # TODO: is it possible to use a shorter timeout?
        upload_id = self._create_upload_id(object_key, "application/octet-stream")
        self._abort_upload_id(upload_id, object_key)

    @classmethod
    def from_storage(cls, storage: Storage) -> MultipartManager:
        try:
            from storages.backends.s3 import S3Storage  # noqa: PLC0415
        except ImportError:
            pass
        else:
            if isinstance(storage, S3Storage):
                from ._multipart_s3 import S3MultipartManager  # noqa: PLC0415

                return S3MultipartManager(storage)

        try:
            from minio_storage.storage import MinioStorage  # noqa: PLC0415
        except ImportError:
            pass
        else:
            if isinstance(storage, MinioStorage):
                from ._multipart_minio import MinioMultipartManager  # noqa: PLC0415

                return MinioMultipartManager(storage)

        raise UnsupportedStorageError

    @classmethod
    def supported_storage(cls, storage: Storage) -> bool:
        try:
            cls.from_storage(storage)
        except UnsupportedStorageError:
            return False
        # Allow other exceptions to propagate
        else:
            return True

    # The AWS default expiration of 1 hour may not be enough for large uploads to complete
    _url_expiration = timedelta(hours=24)

    @abstractmethod
    def _create_upload_id(
        self,
        object_key: str,
        content_type: str,
    ) -> str: ...

    @abstractmethod
    def _abort_upload_id(self, upload_id: str, object_key: str) -> None: ...

    @abstractmethod
    def _generate_presigned_part_url(
        self, upload_id: str, object_key: str, part_number: int, part_size: int
    ) -> str: ...

    @abstractmethod
    def _generate_presigned_complete_url(self, upload_id: str, object_key: str) -> str: ...

    @abstractmethod
    def get_object_size(self, object_key: str) -> int: ...

    @classmethod
    def _iter_part_sizes(cls, file_size: int) -> Iterator[tuple[int, int]]:
        """Yield (part_number, part_size) for a multipart upload."""
        part_size = cls.baseline_part_size

        # If the file would yield too many parts, grow the part size to fit
        if math.ceil(file_size / part_size) > cls.max_parts:
            part_size = math.ceil(file_size / cls.max_parts)

        part_size = max(part_size, cls.min_part_size)
        part_size = min(part_size, cls.max_part_size)

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
