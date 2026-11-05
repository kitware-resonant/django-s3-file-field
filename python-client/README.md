# django-s3-file-field-client
[![PyPI](https://img.shields.io/pypi/v/django-s3-file-field-client)](https://pypi.org/project/django-s3-file-field-client/)

A Python client library for django-s3-file-field.

## Installation
```bash
pip install django-s3-file-field-client
```

## Usage
```python
import mimetypes
import pathlib
import requests
from s3_file_field_client import S3FileFieldClient

file_to_upload = pathlib.Path("/path/to/my_file.txt")
with (
    S3FileFieldClient(
        "http://localhost:8000/api/v1/s3-upload/",  # The path mounted in urlpatterns
        headers={"Authorization": "Token ..."},  # Headers for the API's requests; optional
    ) as s3ff_client,
    file_to_upload.open("rb") as file_stream,  # Open in binary mode
):
    field_value = s3ff_client.upload_file(
        file_stream=file_stream,  # This can be any seekable file-like object
        file_name=file_to_upload.name,
        file_content_type=mimetypes.guess_type(file_to_upload)[0],
        field_id="core.File.blob",  # The "<app>.<model>.<field>" to upload to
    )

requests.post(
    "http://localhost:8000/api/v1/file/",  # This is particular to the application
    headers={"Authorization": "Token ..."},
    json={
        "blob": field_value,  # This should match the field uploaded to (e.g. 'core.File.blob')
        ...: ...,  # Other fields for the POST request
    },
)
```

### Errors
A failed upload raises an `S3FileFieldError`, whose message is suitable for display. Its `status`
is the HTTP status of the response, if one was received, and its `__cause__` is the underlying
`requests` exception, when there is one.
