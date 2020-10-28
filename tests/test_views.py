from django.core.files.storage import default_storage
from django.urls import reverse
import pytest
import requests
from rest_framework.test import APIClient

from .fuzzy import URL_RE, UUID_RE, Re


def mb(bytes_size: int) -> int:
    return bytes_size * 2 ** 20


def test_prepare(api_client):
    resp = api_client.post(
        reverse('s3_file_field:upload-initialize'),
        {'field_id': 'test_app.Resource.blob', 'file_name': 'test.txt', 'file_size': 10},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data == {
        'object_key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
        'parts': [{'part_number': 1, 'size': 10, 'upload_url': URL_RE}],
    }


def test_prepare_two_parts(api_client):
    resp = api_client.post(
        reverse('s3_file_field:upload-initialize'),
        {'field_id': 'test_app.Resource.blob', 'file_name': 'test.txt', 'file_size': mb(10)},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data == {
        'object_key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
        'parts': [
            # 5 MB size
            {'part_number': 1, 'size': mb(5), 'upload_url': URL_RE},
            {'part_number': 2, 'size': mb(5), 'upload_url': URL_RE},
        ],
    }


def test_prepare_three_parts(api_client):
    resp = api_client.post(
        reverse('s3_file_field:upload-initialize'),
        {'field_id': 'test_app.Resource.blob', 'file_name': 'test.txt', 'file_size': mb(12)},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data == {
        'object_key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
        'parts': [
            {'part_number': 1, 'size': mb(5), 'upload_url': URL_RE},
            {'part_number': 2, 'size': mb(5), 'upload_url': URL_RE},
            {'part_number': 3, 'size': mb(2), 'upload_url': URL_RE},
        ],
    }


@pytest.mark.parametrize('file_size', [10, mb(10), mb(12)], ids=['10B', '10MB', '12MB'])
def test_full_upload_flow(api_client: APIClient, file_size: int):
    # Initialize the multipart upload
    resp = api_client.post(
        reverse('s3_file_field:upload-initialize'),
        {'field_id': 'test_app.Resource.blob', 'file_name': 'test.txt', 'file_size': file_size},
        format='json',
    )
    assert resp.status_code == 200
    initialization = resp.data
    assert isinstance(initialization, dict)

    # Perform the upload
    for part in initialization['parts']:
        part_resp = requests.put(part['upload_url'], data=b'a' * part['size'])
        part_resp.raise_for_status()

        # Modify the part to transform it from an initialization to a finalization
        del part['upload_url']
        part['etag'] = part_resp.headers['ETag']

    initialization['field_id'] = 'test_app.Resource.blob'

    # Finalize the upload
    resp = api_client.post(
        reverse('s3_file_field:upload-finalize'),
        initialization,
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data == {
        'field_value': Re(r'.*:.*'),
    }

    # Verify the object is present in the store
    assert default_storage.exists(initialization['object_key'])
