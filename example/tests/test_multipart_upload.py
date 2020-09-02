import json

from fuzzy import URL_RE, UUID_RE, Re
import pytest
import requests


def test_prepare(api_client, boto_client, bucket):
    # contents has length 10B
    contents = b'ten bytes\n'

    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps({'name': 'test.txt', 'content_length': len(contents)}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.json() == {
        'parts': [{'url': URL_RE, 'part_number': 0, 'content_length': 10}],
        'key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
    }


def test_prepare_two_parts(api_client, boto_client, bucket):
    # contents has length 10MB
    contents = b'ten bytes\n' * 1_000_000

    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps(
            {'name': 'test.txt', 'content_length': len(contents), 'max_part_length': 5_000_000}
        ),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.json() == {
        'parts': [
            {'url': URL_RE, 'part_number': 0, 'content_length': 5_000_000},
            {'url': URL_RE, 'part_number': 1, 'content_length': 5_000_000},
        ],
        'key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
    }


def test_prepare_three_parts(api_client, boto_client, bucket):
    # contents has length 15MB
    contents = b'ten bytes\n' * 1_500_000

    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps(
            {'name': 'test.txt', 'content_length': len(contents), 'max_part_length': 6_000_000}
        ),
        content_type='application/json',
    )
    assert resp.status_code == 200
    assert resp.json() == {
        'parts': [
            {'url': URL_RE, 'part_number': 0, 'content_length': 6_000_000},
            {'url': URL_RE, 'part_number': 1, 'content_length': 6_000_000},
            {'url': URL_RE, 'part_number': 2, 'content_length': 3_000_000},
        ],
        'key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
    }


def test_prepare_small_max_part_length_fails(api_client, boto_client, bucket):
    contents = b'File contents!\n'

    with pytest.raises(ValueError) as excinfo:
        api_client.post(
            '/api/joist/multipart-upload-prepare/',
            json.dumps(
                {'name': 'test.txt', 'content_length': len(contents), 'max_part_length': 4_999_999}
            ),
            content_type='application/json',
        )
    assert 'max_part_length must be greater than 5MB' in str(excinfo.value)


def test_finalize(api_client, boto_client, bucket):
    # contents has length 10B
    contents = b'ten bytes\n'

    # Initialize the multipart upload
    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps({'name': 'test.txt', 'content_length': len(contents)}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    resp_json = resp.json()
    assert resp_json == {
        'parts': [{'url': URL_RE, 'part_number': 0, 'content_length': 10}],
        'key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
    }
    key = resp_json['key']
    upload_id = resp_json['upload_id']
    parts = resp_json['parts']

    # Perform the upload
    resp = requests.put(parts[0]['url'], data=contents)
    assert resp.status_code == 200
    etag = resp.headers['ETag']

    # Finalize the upload
    resp = api_client.post(
        '/api/joist/multipart-upload-finalize/',
        json.dumps(
            {'key': key, 'upload_id': upload_id, 'parts': [{'part_number': 0, 'etag': etag}]}
        ),
        content_type='application/json',
    )
    assert resp.status_code == 201

    # Verify the object is present in the store
    resp = boto_client.get_object(Bucket=bucket, Key=key)
    assert resp['Body'].read() == contents


def test_finalize_two_parts(api_client, boto_client, bucket):
    # contents has length 12MB
    # Minio seems to have a slightly higher cap than 5MB, so we will use a max part of 6MB
    contents = b'ten bytes\n' * 1_200_000

    # Initialize the multipart upload
    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps(
            {'name': 'test.txt', 'content_length': len(contents), 'max_part_length': 6_000_000}
        ),
        content_type='application/json',
    )
    assert resp.status_code == 200
    resp_json = resp.json()
    assert resp_json == {
        'parts': [
            {'url': URL_RE, 'part_number': 0, 'content_length': 6_000_000},
            {'url': URL_RE, 'part_number': 1, 'content_length': 6_000_000},
        ],
        'key': Re(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt'),
        'upload_id': UUID_RE,
    }
    key = resp_json['key']
    upload_id = resp_json['upload_id']
    parts = resp_json['parts']

    # Perform the upload
    resp = requests.put(parts[0]['url'], data=contents[:6_000_000])
    assert resp.status_code == 200
    etag0 = resp.headers['ETag']
    resp = requests.put(parts[1]['url'], data=contents[6_000_000:])
    assert resp.status_code == 200
    etag1 = resp.headers['ETag']

    # Finalize the upload
    resp = api_client.post(
        '/api/joist/multipart-upload-finalize/',
        json.dumps(
            {
                'key': key,
                'upload_id': upload_id,
                'parts': [{'part_number': 0, 'etag': etag0}, {'part_number': 1, 'etag': etag1}],
            }
        ),
        content_type='application/json',
    )
    assert resp.status_code == 201

    # Verify the object is present in the store
    resp = boto_client.get_object(Bucket=bucket, Key=key)
    assert resp['Body'].read() == contents
