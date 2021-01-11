# django-s3-file-field-client
[![PyPI](https://img.shields.io/pypi/v/django-s3-file-field-client)](https://pypi.org/project/django-s3-file-field-client/)

A Python client library for django-s3-file-field.

## Usage
```python
from s3_file_field_client import S3FileFieldClient

s3ff_client = S3FileFieldClient(
    'http://localhost:8000/api/v1/s3-upload/',  # The path mounted in urlpatterns
)
with open('/path/to/my_file.txt') as file_stream:
    s3ff_client.upload_file(
        file_stream,  # This can be any file-like object
        'my_file.txt',
        'core.File.blob'  # The "<app>.<model>.<field>" to upload to
    )
```
