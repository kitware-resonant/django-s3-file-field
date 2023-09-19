from typing import Dict, cast

from django.core import signing
from django.core.files.storage import Storage, default_storage
from django.urls import reverse
import pytest
import requests
from rest_framework.test import APIClient

from s3_file_field._sizes import mb

from fuzzy import FUZZY_UPLOAD_ID, FUZZY_URL, Fuzzy


def test_prepare(api_client):
    resp = api_client.post(
        reverse("s3_file_field:upload-initialize"),
        {"field_id": "test_app.Resource.blob", "file_name": "test.txt", "file_size": 10},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data == {
        "object_key": Fuzzy(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt"
        ),
        "upload_id": FUZZY_UPLOAD_ID,
        "parts": [{"part_number": 1, "size": 10, "upload_url": FUZZY_URL}],
        "upload_signature": Fuzzy(r".*:.*"),
    }
    assert signing.loads(resp.data["upload_signature"]) == {
        "object_key": Fuzzy(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt"
        ),
        "field_id": "test_app.Resource.blob",
    }


def test_prepare_two_parts(api_client):
    resp = api_client.post(
        reverse("s3_file_field:upload-initialize"),
        {"field_id": "test_app.Resource.blob", "file_name": "test.txt", "file_size": mb(10)},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data == {
        "object_key": Fuzzy(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt"
        ),
        "upload_id": FUZZY_UPLOAD_ID,
        "parts": [
            # 5 MB size
            {"part_number": 1, "size": mb(5), "upload_url": FUZZY_URL},
            {"part_number": 2, "size": mb(5), "upload_url": FUZZY_URL},
        ],
        "upload_signature": Fuzzy(r".*:.*"),
    }


def test_prepare_three_parts(api_client):
    resp = api_client.post(
        reverse("s3_file_field:upload-initialize"),
        {"field_id": "test_app.Resource.blob", "file_name": "test.txt", "file_size": mb(12)},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data == {
        "object_key": Fuzzy(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/test.txt"
        ),
        "upload_id": FUZZY_UPLOAD_ID,
        "parts": [
            {"part_number": 1, "size": mb(5), "upload_url": FUZZY_URL},
            {"part_number": 2, "size": mb(5), "upload_url": FUZZY_URL},
            {"part_number": 3, "size": mb(2), "upload_url": FUZZY_URL},
        ],
        "upload_signature": Fuzzy(r".*:.*"),
    }


@pytest.mark.parametrize("file_size", [10, mb(10), mb(12)], ids=["10B", "10MB", "12MB"])
@pytest.mark.parametrize(
    "content_type",
    [None, "image/png", "application/dicom"],
    ids=["none", "png", "dicom"],
)
def test_full_upload_flow(
    api_client: APIClient,
    file_size: int,
    content_type: str,
):
    request_body = {
        "field_id": "test_app.Resource.blob",
        "file_name": "test.txt",
        "file_size": file_size,
    }
    # Only include Content headers if non-null
    if content_type is not None:
        request_body["content_type"] = content_type

    # Initialize the multipart upload
    resp = api_client.post(reverse("s3_file_field:upload-initialize"), request_body, format="json")
    assert resp.status_code == 200
    initialization = resp.data
    assert isinstance(initialization, dict)
    upload_signature = initialization["upload_signature"]

    # Perform the upload
    for part in initialization["parts"]:
        part_resp = requests.put(part["upload_url"], data=b"a" * part["size"], timeout=5)
        part_resp.raise_for_status()

        # Modify the part to transform it from an initialization to a finalization
        del part["upload_url"]
        part["etag"] = part_resp.headers["ETag"]

    initialization["field_id"] = "test_app.Resource.blob"

    # Presign the complete request
    resp = api_client.post(
        reverse("s3_file_field:upload-complete"),
        {
            "upload_id": initialization["upload_id"],
            "parts": initialization["parts"],
            "upload_signature": upload_signature,
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data == {
        "complete_url": Fuzzy(r".*"),
        "body": Fuzzy(r".*"),
    }
    completion_data = cast(Dict, resp.data)

    # Complete the upload
    complete_resp = requests.post(
        completion_data["complete_url"],
        data=completion_data["body"],
        timeout=5,
    )
    complete_resp.raise_for_status()

    # Fix https://github.com/typeddjango/django-stubs/issues/1610
    assert isinstance(default_storage, Storage)
    # Verify the object is present in the store
    assert default_storage.exists(initialization["object_key"])

    # Finalize the upload
    resp = api_client.post(
        reverse("s3_file_field:finalize"),
        {
            "upload_signature": upload_signature,
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data == {
        "field_value": Fuzzy(r".*:.*"),
    }

    # Verify that the Content headers were stored correctly on the object
    object_resp = requests.get(default_storage.url(initialization["object_key"]), timeout=5)
    assert resp.status_code == 200
    if content_type is not None:
        assert object_resp.headers["Content-Type"] == content_type

    default_storage.delete(initialization["object_key"])
