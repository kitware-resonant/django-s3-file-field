from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import minio

from ._multipart import MultipartManager, ObjectNotFoundError, TransferredParts
from ._sizes import tb

if TYPE_CHECKING:
    from minio_storage.storage import MinioStorage


class MinioMultipartManager(MultipartManager):
    # MinIO limits: https://min.io/docs/minio/container/operations/checklists/thresholds.html
    max_object_size = tb(50)

    def __init__(self, storage: MinioStorage):
        self._client: minio.Minio = storage.client
        self._bucket_name: str = storage.bucket_name
        # To support MinioStorage's "base_url" functionality, an alternative client must be used
        # for pre-signing URLs when it exists
        self._signing_client: minio.Minio = getattr(storage, "base_url_client", storage.client)

    def _create_upload_id(
        self,
        object_key: str,
        content_type: str,
        acl: Optional[str] = None,
    ) -> str:
        return self._client._create_multipart_upload(
            bucket_name=self._bucket_name,
            object_name=object_key,
            headers={
                "Content-Type": content_type,
            },
            # TODO: filename in headers
        )

    def _abort_upload_id(self, object_key: str, upload_id: str) -> None:
        self._client._abort_multipart_upload(
            bucket_name=self._bucket_name,
            object_name=object_key,
            upload_id=upload_id,
        )

    def _generate_presigned_part_url(
        self, object_key: str, upload_id: str, part_number: int, part_size: int
    ) -> str:
        return self._signing_client.get_presigned_url(
            method="PUT",
            bucket_name=self._bucket_name,
            object_name=object_key,
            expires=self._url_expiration,
            # Both "extra_query_params" and "response_headers" add a query string, but
            # "extra_query_params" does not sign them properly and results in incorrect URL syntax
            response_headers={
                "uploadId": upload_id,
                "partNumber": str(part_number),
                # MinIO server does not seem to enforce presigning of "Content-Length"
            },
        )

    def _generate_presigned_complete_url(self, transferred_parts: TransferredParts) -> str:
        return self._signing_client.get_presigned_url(
            method="POST",
            bucket_name=self._bucket_name,
            object_name=transferred_parts.object_key,
            expires=self._url_expiration,
            response_headers={
                "uploadId": transferred_parts.upload_id,
            },
        )

    def get_object_size(self, object_key: str) -> int:
        try:
            stats = self._client.stat_object(bucket_name=self._bucket_name, object_name=object_key)
        except minio.S3Error as e:
            if e.code == "NoSuchKey":
                raise ObjectNotFoundError from e
            raise
        if stats.size is None:
            raise RuntimeError("MinIO did not return a size for object.", object_key)
        return stats.size
