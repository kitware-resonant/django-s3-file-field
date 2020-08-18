import pytest
from rest_framework.test import APIClient

from s3_file_field.boto import client_factory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def boto_client():
    return client_factory('s3')
