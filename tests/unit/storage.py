from dataclasses import dataclass
import os
from typing import TYPE_CHECKING, Optional

from botocore.exceptions import ClientError
from minio import Minio
from minio_storage.storage import MinioStorage

if TYPE_CHECKING:
    # mypy_boto3_s3 only provides types
    import mypy_boto3_s3 as s3

    # S3Boto3Storage requires Django settings to be available at import time
    from storages.backends.s3boto3 import S3Boto3Storage


@dataclass
class S3ConnectionParams:
    endpoint: str
    endpoint_secure: bool
    region: str
    access_key: str
    secret_key: str
    bucket_name: str


def _get_s3_connection_params() -> S3ConnectionParams:
    return S3ConnectionParams(
        endpoint=os.environ['MINIO_STORAGE_ENDPOINT'],
        endpoint_secure=False,
        region='test-region',
        access_key=os.environ['MINIO_STORAGE_ACCESS_KEY'],
        secret_key=os.environ['MINIO_STORAGE_SECRET_KEY'],
        bucket_name=os.environ['MINIO_STORAGE_MEDIA_BUCKET_NAME'],
    )


def s3boto3_storage_factory(
    s3_connection_params: Optional[S3ConnectionParams] = None,
) -> 'S3Boto3Storage':
    if s3_connection_params is None:
        s3_connection_params = _get_s3_connection_params()

    from storages.backends.s3boto3 import S3Boto3Storage

    # Don't use Django settings, as we want to test that arbitrary storage instances,
    # not just media storage, are compatible
    storage = S3Boto3Storage(
        access_key=s3_connection_params.access_key,
        secret_key=s3_connection_params.secret_key,
        region_name=s3_connection_params.region,
        bucket_name=s3_connection_params.bucket_name,
        # For testing, connect to a local Minio instance
        endpoint_url=(
            f'{"https" if s3_connection_params.endpoint_secure else "http"}:'
            f'//{s3_connection_params.endpoint}'
        ),
    )

    resource: s3.ServiceResource = storage.connection
    client: s3.Client = resource.meta.client
    try:
        client.head_bucket(Bucket=s3_connection_params.bucket_name)
    except ClientError:
        client.create_bucket(Bucket=s3_connection_params.bucket_name)

    return storage


def minio_storage_factory(
    s3_connection_params: Optional[S3ConnectionParams] = None,
) -> MinioStorage:
    if s3_connection_params is None:
        s3_connection_params = _get_s3_connection_params()

    return MinioStorage(
        minio_client=Minio(
            endpoint=s3_connection_params.endpoint,
            secure=s3_connection_params.endpoint_secure,
            access_key=s3_connection_params.access_key,
            secret_key=s3_connection_params.secret_key,
            # Don't use s3_connection_params.region, let Minio set its own value internally
        ),
        bucket_name=s3_connection_params.bucket_name,
        auto_create_bucket=True,
        presign_urls=True,
        # TODO: Test the case of an alternate base_url
        # base_url='http://minio:9000/bucket-name'
    )
