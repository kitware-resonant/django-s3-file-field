import io
import json
from typing import Dict

from django.core import signing
import pytest

from s3_file_field.testing import S3FileFieldTestClient

# Create test json file
test_json_str = json.dumps(
    {
        'a': 1,
        'b': 2,
        'c': 3,
        'd': 4,
    }
)


@pytest.fixture
def s3ff_client(api_client):
    return S3FileFieldTestClient(api_client, '/api/s3ff_test')


@pytest.mark.django_db
def test_field_value(s3ff_client):
    with io.StringIO(test_json_str) as file_stream:
        field_value = s3ff_client.upload_file(file_stream, 'test.json', 'test_app.Resource.blob')

    # Verifies that the response is in a correct format
    loaded_dict: Dict = signing.loads(field_value)

    assert 'object_key' in loaded_dict
    assert 'file_size' in loaded_dict
