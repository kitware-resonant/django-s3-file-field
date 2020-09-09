import json

from django.core.files.storage import default_storage
import pytest
import requests

from .fuzzy import URL_RE, UUID_RE, Re


def mb(bytes_size: int) -> int:
    return bytes_size * 2 ** 20


def test_prepare(api_client):
    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps({'name': 'test.txt', 'content_length': 10}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.data == {
        'object_key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
        'parts': [{'part_number': 1, 'size': 10, 'upload_url': URL_RE}],
    }


def test_prepare_two_parts(api_client):
    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps({'name': 'test.txt', 'content_length': mb(10), 'max_part_length': mb(5)}),
        content_type='application/json',
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
        '/api/joist/multipart-upload-prepare/',
        json.dumps({'name': 'test.txt', 'content_length': mb(20), 'max_part_length': mb(7)}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.data == {
        'object_key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
        'parts': [
            {'part_number': 1, 'size': mb(7), 'upload_url': URL_RE},
            {'part_number': 2, 'size': mb(7), 'upload_url': URL_RE},
            {'part_number': 3, 'size': mb(6), 'upload_url': URL_RE},
        ],
    }


@pytest.mark.skip
def test_prepare_small_max_part_length_fails(api_client):
    contents = b'File contents!\n'

    with pytest.raises(ValueError, match='max_part_length must be greater than 5MB'):
        api_client.post(
            '/api/joist/multipart-upload-prepare/',
            json.dumps(
                {'name': 'test.txt', 'content_length': len(contents), 'max_part_length': 4_999_999}
            ),
            content_type='application/json',
        )


@pytest.mark.parametrize('content_size', [10, mb(10), mb(100)], ids=['10B', '10MB', '10GB'])
def test_full_upload_flow(api_client, content_size):
    # Initialize the multipart upload
    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps({'name': 'test.txt', 'content_length': content_size, 'max_part_length': mb(5)}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    multipart_initialization = resp.data

    # Perform the upload
    for part in multipart_initialization['parts']:
        # Ensure the test is sane, with multiple-of-10 part sizes
        assert part['size'] % 10 == 0
        part_content = b'ten bytes\n' * int(part['size'] / 10)
        resp = requests.put(part['upload_url'], data=part_content)
        assert resp.status_code == 200

        # Modify the part to transform it from an initialization to a finalization
        del part['upload_url']
        part['etag'] = resp.headers['ETag']

    # Finalize the upload
    resp = api_client.post(
        '/api/joist/multipart-upload-finalize/',
        json.dumps(multipart_initialization),
        content_type='application/json',
    )
    assert resp.status_code == 201

    # Verify the object is present in the store
    assert default_storage.exists(multipart_initialization['object_key'])
