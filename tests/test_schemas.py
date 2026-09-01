from __future__ import annotations

from s3_file_field._schemas import UploadInitializationRequestModel


def test_upload_initialization_request_deserialization() -> None:
    UploadInitializationRequestModel.model_validate(
        {
            "field_id": "test_app.Resource.blob",
            "file_name": "test-name.jpg",
            "file_size": 15,
            "content_type": "image/jpeg",
        }
    )
