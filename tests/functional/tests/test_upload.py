import json


def test_upload_prepare(api_client):
    resp = api_client.post(
        '/api/joist/upload-prepare/',
        json.dumps({'name': 'test.txt'}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    resp_json = resp.json()
    assert 's3Options' in resp_json
    assert 'bucketName' in resp_json
    assert 'objectKey' in resp_json
    assert 'signature' in resp_json
