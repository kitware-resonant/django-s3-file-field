from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rest_framework.test import APIClient

from factories import UploadTokenFactory
from s3_file_field._multipart import MultipartManager
from s3_file_field._sizes import mb

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from s3_file_field._schemas import UploadToken

# Explicitly load s3_file_field fixtures, late in Pytest plugin load order.
# If this is auto-loaded via entry point, the import happens before coverage tracing is started by
# pytest-cov, and import-time code doesn't get covered.
# See https://pytest-cov.readthedocs.io/en/latest/plugins.html for a description of the problem.
# See
# https://docs.pytest.org/en/7.1.x/how-to/writing_plugins.html#plugin-discovery-order-at-tool-startup
# for info on Pytest plugin load order.
pytest_plugins = ["s3_file_field.fixtures"]


@pytest.fixture(autouse=True)
def _reduce_baseline_part_size(mocker: MockerFixture) -> None:
    """To speed up tests, reduce the baseline part size to the minimum supported by S3 (5MB)."""
    mocker.patch.object(MultipartManager, "baseline_part_size", new=mb(5))


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def upload_token() -> UploadToken:
    return UploadTokenFactory.build()
