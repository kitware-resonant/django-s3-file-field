import pytest
from rest_framework.test import APIClient

from test_app.models import Resource


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def resource() -> Resource:
    return Resource()
