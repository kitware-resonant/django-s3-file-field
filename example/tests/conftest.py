import pytest
from rest_framework.test import APIClient

from s3_file_field import constants
from s3_file_field.boto import client_factory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def boto_client():
    return client_factory('s3')


@pytest.fixture
def bucket(boto_client):
    # Possibly due to lifecycle ordering, where a Boto instance is
    # created before a Storage, MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET
    # does not trigger bucket creation as intended.
    resp = boto_client.list_buckets()
    for bucket in resp['Buckets']:
        if bucket['Name'] == constants.S3FF_BUCKET:
            return constants.S3FF_BUCKET
    # If the bucket doesn't exist yet, create it
    boto_client.create_bucket(Bucket=constants.S3FF_BUCKET)
    return constants.S3FF_BUCKET
