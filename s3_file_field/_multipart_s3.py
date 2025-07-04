from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from botocore.exceptions import ClientError

from ._sizes import tb

if TYPE_CHECKING:
    # mypy_boto3_s3 only provides types
    import mypy_boto3_s3 as s3
    from storages.backends.s3 import S3Storage

from ._multipart import MultipartManager, ObjectNotFoundError, TransferredParts


class S3MultipartManager(MultipartManager):
    # S3 multipart limits: https://docs.aws.amazon.com/AmazonS3/latest/dev/qfacts.html
    max_object_size = tb(5)

    def __init__(self, storage: S3Storage) -> None:
        resource: s3.ServiceResource = storage.connection
        self._client: s3.Client = resource.meta.client
        self._bucket_name: str = storage.bucket_name

    def _create_upload_id(
        self,
        object_key: str,
        content_type: str,
        acl: Optional[str] = None,
    ) -> str:
        kwargs: dict[str, Any] = {}
        if acl:
            kwargs["ACL"] = acl
        resp = self._client.create_multipart_upload(
            Bucket=self._bucket_name,
            Key=object_key,
            ContentType=content_type,
            # TODO: filename in Metadata
            # TODO: ensure ServerSideEncryption is set, even if not specified
            # TODO: use client._get_write_parameters?
            **kwargs,
        )
        return resp["UploadId"]

    def _abort_upload_id(self, object_key: str, upload_id: str) -> None:
        self._client.abort_multipart_upload(
            Bucket=self._bucket_name,
            Key=object_key,
            UploadId=upload_id,
        )

    def _generate_presigned_part_url(
        self, object_key: str, upload_id: str, part_number: int, part_size: int
    ) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="upload_part",
            Params={
                "Bucket": self._bucket_name,
                "Key": object_key,
                "UploadId": upload_id,
                "PartNumber": part_number,
                "ContentLength": part_size,
            },
            ExpiresIn=int(self._url_expiration.total_seconds()),
        )

    def _generate_presigned_complete_url(self, transferred_parts: TransferredParts) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="complete_multipart_upload",
            Params={
                "Bucket": self._bucket_name,
                "Key": transferred_parts.object_key,
                "UploadId": transferred_parts.upload_id,
            },
            ExpiresIn=int(self._url_expiration.total_seconds()),
        )

    def get_object_size(self, object_key: str) -> int:
        try:
            stats = self._client.head_object(
                Bucket=self._bucket_name,
                Key=object_key,
            )
            return stats["ContentLength"]
        except ClientError as e:
            raise ObjectNotFoundError from e
