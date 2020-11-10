import minio
from minio_storage.storage import MinioStorage

from ._multipart import MultipartManager, UploadCompletion


class MinioMultipartManager(MultipartManager):
    def __init__(self, storage: MinioStorage):
        self._client: minio.Minio = storage.client
        self._bucket_name: str = storage.bucket_name
        # To support MinioStorage's "base_url" functionality, an alternative client must be used
        # for pre-signing URLs when it exists
        self._signing_client: minio.Minio = getattr(storage, 'base_url_client', storage.client)

    def _create_upload_id(self, object_key: str) -> str:
        return self._client._new_multipart_upload(
            bucket_name=self._bucket_name,
            object_name=object_key,
            # TODO: filename in Metadata
        )

    def _abort_upload_id(self, object_key: str, upload_id: str) -> None:
        self._client._remove_incomplete_upload(
            bucket_name=self._bucket_name,
            object_name=object_key,
            upload_id=upload_id,
        )

    def _generate_presigned_part_url(
        self, object_key: str, upload_id: str, part_number: int, part_size: int
    ) -> str:
        return self._signing_client.presigned_url(
            method='PUT',
            bucket_name=self._bucket_name,
            object_name=object_key,
            expires=self._url_expiration,
            # Both "extra_query_params" and "response_headers" add a query string, but
            # "extra_query_params" does not sign them properly and results in incorrect URL syntax
            response_headers={
                'uploadId': upload_id,
                'partNumber': str(part_number),
            },
            # TODO: presigned_url does not allow arbitrary headers, but presign_v4 within it does
            # headers={
            #     'Content-Length': str(part_size)
            # }
        )

    def _generate_presigned_complete_url(self, completion: UploadCompletion) -> str:
        return self._signing_client.presigned_url(
            method='POST',
            bucket_name=self._bucket_name,
            object_name=completion.object_key,
            expires=self._url_expiration,
            response_headers={
                'uploadId': completion.upload_id,
            },
        )

    def get_upload_size(self, object_key: str) -> int:
        try:
            stats = self._client.stat_object(bucket_name=self._bucket_name, object_name=object_key)
            return stats.size
        except minio.error.NoSuchKey:
            raise ValueError('Object not found')
