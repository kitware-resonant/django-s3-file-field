from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, override

from botocore.exceptions import ClientError

from ._sizes import tb

if TYPE_CHECKING:
    # mypy_boto3_s3 only provides types
    import mypy_boto3_s3 as s3
    from storages.backends.s3 import S3Storage

from ._multipart import MultipartManager, ObjectNotFoundError


class S3MultipartManager(MultipartManager):
    # S3 multipart limits: https://docs.aws.amazon.com/AmazonS3/latest/dev/qfacts.html
    max_object_size = tb(5)

    def __init__(self, storage: S3Storage) -> None:
        resource: s3.ServiceResource = storage.connection
        self._client: s3.Client = resource.meta.client
        self._bucket_name: str = storage.bucket_name

    @property
    def presigns_with_sigv4(self) -> bool:
        """Return whether presigned URLs will be signed with Signature Version 4."""
        # When no signature version is explicitly configured (via a botocore Config, a
        # django-storages setting, or the AWS config file), botocore registers a client
        # event handler which, for backwards compatibility, downgrades presigning (only)
        # to SigV2 in legacy AWS regions; the client's resolved config still reports
        # "s3v4", so it cannot be trusted here.
        # "_choose_signer" runs the actual "choose-signer" event chain, so this is exactly
        # the decision that presigning will make; it generates nothing and needs no
        # credentials. Presigning with SigV4 yields "s3v4-query".
        signature_version = self._client._request_signer._choose_signer(  # type: ignore[attr-defined]  # noqa: SLF001
            "UploadPart", "presign-url", {}
        )
        # A non-string (the botocore.UNSIGNED sentinel) is correctly reported as False
        return str(signature_version) == "s3v4-query"

    @override
    def _create_upload_id(
        self,
        object_key: str,
        content_type: str,
    ) -> str:
        resp = self._client.create_multipart_upload(
            Bucket=self._bucket_name,
            Key=object_key,
            ContentType=content_type,
            # TODO: filename in Metadata
            # TODO: ensure ServerSideEncryption is set, even if not specified
            # TODO: use client._get_write_parameters?
        )
        return resp["UploadId"]

    @override
    def _abort_upload_id(self, upload_id: str, object_key: str) -> None:
        self._client.abort_multipart_upload(
            Bucket=self._bucket_name,
            Key=object_key,
            UploadId=upload_id,
        )

    @override
    def _generate_presigned_part_url(
        self, upload_id: str, object_key: str, part_number: int, part_size: int
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

    @override
    def _generate_presigned_complete_url(self, upload_id: str, object_key: str) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="complete_multipart_upload",
            Params={
                "Bucket": self._bucket_name,
                "Key": object_key,
                "UploadId": upload_id,
            },
            ExpiresIn=int(self._url_expiration.total_seconds()),
        )

    @override
    def get_object_size(self, object_key: str) -> int:
        try:
            stats = self._client.head_object(
                Bucket=self._bucket_name,
                Key=object_key,
            )
            return stats["ContentLength"]
        except ClientError as e:
            if e.response["ResponseMetadata"]["HTTPStatusCode"] == HTTPStatus.NOT_FOUND:
                raise ObjectNotFoundError from e
            raise
