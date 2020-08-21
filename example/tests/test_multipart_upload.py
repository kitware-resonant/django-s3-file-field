import json

import requests


def test_multipart_upload(api_client, boto_client, bucket):
    # Initialize the multipart upload
    resp = api_client.post(
        '/api/joist/multipart-upload-prepare/',
        json.dumps({'name': 'test.txt', 'parts': 1}),
        content_type='application/json',
    )
    assert resp.status_code == 200

    resp_json = resp.json()
    key = resp_json['key']
    upload_id = resp_json['upload_id']
    parts = resp_json['parts']

    assert len(parts) == 1
    assert parts[0]['part_number'] == 0
    upload_url = parts[0]['url']

    # Perform the upload
    contents = b'File contents!\n'
    resp = requests.put(upload_url, data=contents)
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
