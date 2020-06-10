# django-s3-file-field

[![PyPI version
 shields.io](https://img.shields.io/pypi/v/django-s3-file-field.svg)](https://pypi.python.org/pypi/django-s3-file-field/)
![PyPI - Python
 Version](https://img.shields.io/pypi/pyversions/django-s3-file-field)
![PyPI - Django Version](https://img.shields.io/pypi/djversions/django-s3-file-field)

`django-s3-file-field` is a Django widget library for uploading files directly to S3
(or MinIO) through the browser. django-s3-file-field heavily depends on the
[django-storages](https://github.com/jschneier/django-storages) package.

## Quickstart
Ensure you've configured your Django installation to use `django-storages` for S3 access: https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html.

Install the django-s3-file-field package:
```sh
pip install django-s3-file-field
```

Add `s3_file_field` to your `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
 ...
 's3_file_field',
]
```

Add the required settings:
```python
S3FF_UPLOAD_STS_ARN = '' # see STS Role section below (not required for minio)
```

Add the appropriate routes to `urls.py`:
```python
urlpatterns = [
    ...
    path('api/s3-upload/', include('s3_file_field.urls')),
]
```


## Usage
```python
from s3_file_field import S3FileField

class Car(db.Model):
    ...
    owners_manual = S3FileField()
```


## Running checks

django-s3-file-field can detect common misconfigurations using Django's built in [System check
framework](https://docs.djangoproject.com/en/3.0/topics/checks/). To confirm
your configuration is correct, run:

``` sh
./manage.py check
```


## Advanced Topics

### Advanced configuration

| Key                  | Default          | Description                                 |
| -------------------  | ---------------- | ------------------------------------------- |
| S3FF_UPLOAD_STS_ARN  | none             | ...                                         |


#### STS configuration
#### CORS configuration

This is a minimal function CORS configuration for an S3 bucket to be compatible with django-s3-file-field:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<CORSRule>
    <AllowedHeader>*</AllowedHeader>
    <AllowedMethod>POST</AllowedMethod>
    <AllowedMethod>PUT</AllowedMethod>
    <AllowedOrigin>*</AllowedOrigin>
    <ExposeHeader>Connection</ExposeHeader>
    <ExposeHeader>Content-Length</ExposeHeader>
    <ExposeHeader>Date</ExposeHeader>
    <ExposeHeader>ETag</ExposeHeader>
    <ExposeHeader>Server</ExposeHeader>
    <ExposeHeader>x-amz-delete-marker</ExposeHeader>
    <ExposeHeader>x-amz-version-id</ExposeHeader>
    <MaxAgeSeconds>600</MaxAgeSeconds>
</CORSRule>
</CORSConfiguration>
```

Note: These are insecure defaults, the allowed origin and headers should not be a wildcard but instead
modified for your specific deployment(s).

### MinIO support
MinIO support depends on the django-minio-storage config (see https://django-minio-storage.readthedocs.io/en/latest/usage/), following settings are used

### Security considerations


### Integrating with forms
 note on form.media


### Extending

django-s3-file-field sends out two signals when its REST api is called:

```python
s3_file_field_upload_prepare(field_value: str, object_key: str)
s3_file_field_upload_finalize(name: str, object_key: str, status: string)
```
### API Reference
