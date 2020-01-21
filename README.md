# joist

[![PyPI version shields.io](https://img.shields.io/pypi/v/joist.svg)](https://pypi.python.org/pypi/joist/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/joist) ![PyPI - Django Version](https://img.shields.io/pypi/djversions/joist)

joist is a Django library for uploading files directly to S3 (or MinIO) through the browser. joist heavily depends on the [django-storages](https://github.com/jschneier/django-storages) package.

## Quickstart
Ensure you've configured your Django installation to use `django-storages` for S3 access: https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html.

Install the joist package:
```sh
pip install joist
```

Add `joist` to your `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
 ...
 'joist',
]
```

Add the required settings:
```python
JOIST_UPLOAD_STS_ARN = '' # see STS Role section below
```

Add the joist routes to `urls.py`:
```python
urlpatterns = [
    ...
    path('api/joist/', include('joist.urls')),
]
```


## Usage
```python
from joist.fields import S3FileField

class Car(db.Model):
    ...
    owners_manual = S3FileField()
```



## Advanced Topics

### Advanced configuration

| Key                  | Default      | Description                                 |
| -------------------  | ------------ | ------------------------------------------- |
| JOIST_UPLOAD_STS_ARN | none         | ...                                         |
| JOIST_UPLOAD_PREFIX  | none         | Prefix where files should be stored         |
| JOIST_API_BASE_URL   | `/api/joist` | API prefix where the server urls are hosted |


#### STS configuration
#### CORS configuration

This is a minimal function CORS configuration for an S3 bucket to be compatible with joist:

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

Joist sends out two signals when its REST api is called:

```python
joist_upload_prepare(name: str, object_key: str)
joist_upload_finalize(name: str, object_key: str, status: string)
```
### API Reference
