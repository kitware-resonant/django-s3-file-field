from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # mypy_boto3_s3 only provides types
    import mypy_boto3_s3 as s3

    # S3Boto3Storage requires Django settings to be available at import time
    from storages.backends.s3boto3 import S3Boto3Storage

from ._multipart import MultipartManager, UploadFinalization


class Boto3MultipartManager(MultipartManager):
    def __init__(self, storage: 'S3Boto3Storage'):
        resource: s3.ServiceResource = storage.connection
        self._client: s3.Client = resource.meta.client
        self._bucket_name: str = storage.bucket_name

    def _create_upload_id(self, object_key: str) -> str:
        resp = self._client.create_multipart_upload(
            Bucket=self._bucket_name,
            Key=object_key,
            # TODO: filename in Metadata
            # TODO: ContentType
            # TODO: ContentEncoding
            # TODO: ensure ServerSideEncryption is set, even if not specified
            # TODO: use client._get_write_parameters?
        )
        return resp['UploadId']

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
            ClientMethod='upload_part',
            Params={
                'Bucket': self._bucket_name,
                'Key': object_key,
                'UploadId': upload_id,
                'PartNumber': part_number,
                'ContentLength': part_size,
            },
            ExpiresIn=int(self._url_expiration.total_seconds()),
        )

    def finalize_upload(self, finalization: UploadFinalization) -> None:
        # TODO: from
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.complete_multipart_upload
        # "Processing of a Complete Multipart Upload request could
        # take several minutes to complete."
        self._client.complete_multipart_upload(
            Bucket=self._bucket_name,
            Key=finalization.object_key,
            UploadId=finalization.upload_id,
            MultipartUpload={
                'Parts': [
                    {
                        'PartNumber': part.part_number,
                        'ETag': part.etag,
                    }
                    for part in finalization.parts
                ],
            },
        )
