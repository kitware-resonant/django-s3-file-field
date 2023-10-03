from datetime import datetime, timedelta
from typing import Any, Mapping

from urllib3 import PoolManager

from .datatypes import Object
from .provider import Provider
from .sse import SseCustomerKey

class Minio:
    def __init__(
        self,
        endpoint: str,
        access_key: str | None = ...,
        secret_key: str | None = ...,
        session_token: str | None = ...,
        secure: bool = ...,
        region: str | None = ...,
        http_client: PoolManager | None = ...,
        credentials: Provider | None = ...,
        cert_check: bool = ...,
    ) -> None: ...
    def stat_object(
        self,
        bucket_name: str,
        object_name: str,
        ssec: SseCustomerKey | None = ...,
        version_id: str | None = ...,
        extra_query_params: Mapping[str, Any] | None = ...,
    ) -> Object: ...
    def get_presigned_url(
        self,
        method: str,
        bucket_name: str,
        object_name: str,
        expires: timedelta = ...,
        response_headers: Mapping[str, Any] | None = ...,
        request_date: datetime | None = ...,
        version_id: str | None = ...,
        extra_query_params: Mapping[str, Any] | None = ...,
    ) -> str: ...
    def _create_multipart_upload(
        self, bucket_name: str, object_name: str, headers: Mapping[str, Any]
    ) -> str: ...
    def _abort_multipart_upload(
        self, bucket_name: str, object_name: str, upload_id: str
    ) -> None: ...
