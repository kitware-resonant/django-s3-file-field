from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files.storage import default_storage
from django.urls import reverse
import pytest
import requests

from fuzzy import FUZZY_POSITIVE_INT, FUZZY_URL, Fuzzy
from s3_file_field._multipart import MultipartManager
from s3_file_field._sizes import mb

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from rest_framework.test import APIClient


@pytest.mark.parametrize(
    ("file_size", "num_parts"),
    [
        (10, 1),
        (mb(10), 2),
        (mb(12), 3),
    ],
    ids=["10B", "10MB", "12MB"],
)
def test_prepare(api_client: APIClient, file_size: int, num_parts: int) -> None:
    resp = api_client.post(
        reverse("s3_file_field:upload-initialize"),
        {
            "field_id": "test_app.Resource.blob",
            "file_name": "test.txt",
            "file_size": file_size,
            "content_type": "text/plain",
        },
        format="json",
    )
    assert resp.status_code == 200
    resp_json = resp.json()
    assert resp_json == {
        "upload_signature": Fuzzy(r"\A.+\Z"),
        "parts": [
            {"part_number": part_num, "size": FUZZY_POSITIVE_INT, "upload_url": FUZZY_URL}
            for part_num in range(1, num_parts + 1)
        ],
    }


def test_prepare_content_type_invalid(api_client: APIClient) -> None:
    resp = api_client.post(
        reverse("s3_file_field:upload-initialize"),
        {
            "field_id": "test_app.Resource.blob",
            "file_name": "test.txt",
            "file_size": 10,
            "content_type": "not a mime type",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert [error["loc"] for error in resp.json()["detail"]] == [["content_type"]]


@pytest.mark.parametrize("file_size", [10, mb(10), mb(12)], ids=["10B", "10MB", "12MB"])
def test_full_upload_flow(
    api_client: APIClient,
    file_size: int,
    mocker: MockerFixture,
) -> None:
    initialize_upload_spy = mocker.spy(MultipartManager, "initialize_upload")

    # Initialize the multipart upload
    resp = api_client.post(
        reverse("s3_file_field:upload-initialize"),
        {
            "field_id": "test_app.Resource.blob",
            "file_name": "test.txt",
            "file_size": file_size,
            "content_type": "text/plain",
        },
        format="json",
    )
    assert resp.status_code == 200
    initialization = resp.json()
    assert isinstance(initialization, dict)
    upload_signature = initialization["upload_signature"]
    # The response does not contain the object_key; capture it from the server internals
    object_key: str = initialize_upload_spy.spy_return.object_key

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
            "upload_signature": upload_signature,
            "parts": initialization["parts"],
        },
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data == {
        "complete_url": Fuzzy(r".*"),
        "body": Fuzzy(r".*"),
    }
    # Complete the upload
    complete_resp = requests.post(
        resp.data["complete_url"],
        data=resp.data["body"],
        timeout=5,
    )
    complete_resp.raise_for_status()

    # Verify the object is present in the store
    assert default_storage.exists(object_key)

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
        "field_value": Fuzzy(r"\A.+\Z"),
    }

    # Verify that the Content headers were stored correctly on the object
    object_resp = requests.get(default_storage.url(object_key), timeout=5)
    assert resp.status_code == 200
    assert object_resp.headers["Content-Type"] == "text/plain"

    default_storage.delete(object_key)
