from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fields import S3FileField

import minio
from minio_storage.storage import MinioStorage

from ._multipart import MultipartManager, UploadFinalization


class MinioMultipartManager(MultipartManager):
    def __init__(self, field: 'S3FileField'):
        super().__init__(field)
        storage: MinioStorage = field.storage
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

    def finalize_upload(self, finalization: UploadFinalization) -> None:
        uploaded_parts = {
            part.part_number: minio.definitions.UploadPart(
                bucket_name=self._bucket_name,
                object_name=finalization.object_key,
                upload_id=finalization.upload_id,
                part_number=part.part_number,
                etag=part.etag,
                size=part.size,
                # Minio doesn't seem to actually use last_modified, and it's burdensome to track
                last_modified=None,
            )
            for part in finalization.parts
        }

        self._client._complete_multipart_upload(
            bucket_name=self._bucket_name,
            object_name=finalization.object_key,
            upload_id=finalization.upload_id,
            uploaded_parts=uploaded_parts,
        )
