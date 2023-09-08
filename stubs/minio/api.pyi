from datetime import datetime, timedelta
from typing import Any, Mapping, Optional

from urllib3 import PoolManager

from .datatypes import Object
from .provider import Provider
from .sse import SseCustomerKey

class Minio:
    def __init__(
        self,
        endpoint: str,
        access_key: Optional[str] = ...,
        secret_key: Optional[str] = ...,
        session_token: Optional[str] = ...,
        secure: bool = ...,
        region: Optional[str] = ...,
        http_client: Optional[PoolManager] = ...,
        credentials: Optional[Provider] = ...,
        cert_check: bool = ...,
    ) -> None: ...
    def stat_object(
        self,
        bucket_name: str,
        object_name: str,
        ssec: Optional[SseCustomerKey] = ...,
        version_id: Optional[str] = ...,
        extra_query_params: Optional[Mapping[str, Any]] = ...,
    ) -> Object: ...
    def get_presigned_url(
        self,
        method: str,
        bucket_name: str,
        object_name: str,
        expires: timedelta=...,
        response_headers: Optional[Mapping[str, Any]] = ...,
        request_date: Optional[datetime] = ...,
        version_id: Optional[str] = ...,
        extra_query_params: Optional[Mapping[str, Any]] = ...,
    ) -> str: ...
    def _create_multipart_upload(
        self, bucket_name: str, object_name: str, headers: Mapping[str, Any]
    ) -> str: ...
    def _abort_multipart_upload(
        self, bucket_name: str, object_name: str, upload_id: str
    ) -> None: ...
