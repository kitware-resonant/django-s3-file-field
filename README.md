# django-s3-file-field
[![PyPI](https://img.shields.io/pypi/v/django-s3-file-field)](https://pypi.org/project/django-s3-file-field/)

django-s3-file-field is a Django library for uploading files directly to
[AWS S3](https://aws.amazon.com/s3/) or [MinIO](https://min.io/) Storage from HTTP clients
(browsers, CLIs, etc.).

### Benefits
django-s3-file-field makes long-running file transfers (with large files or slow connections)
more efficient, as the file content is no longer proxied through the Django server. This also frees
Django from needing to maintain active HTTP requests during file upload, decreasing server load and
facilitating deployment to environments like
[Heroku, which have short, strict request timeouts](https://devcenter.heroku.com/articles/request-timeout).

### Scope
The principal API of django-s3-file-field is the `S3FileField`, which is a subclass of
[Django's `FileField`](https://docs.djangoproject.com/en/4.2/ref/models/fields/#filefield).
django-s3-file-field does not affect any operations other than uploading from external HTTP
clients; for all other file operations (downloading, uploading from the Python API, etc.), refer to
[Django's file management documentation](https://docs.djangoproject.com/en/4.2/topics/files/).

django-s3-file-field supports both the creation and modification (by overwrite) of
`S3FileField`-containing `Model` instances.
It supports server-rendered views, via the Forms API, with Form `Field` and `Widget` subclasses
which will automatically be used for `ModelForm` instances.
It also supports RESTful APIs, via Django Rest Framework's Serializer API, with a
Serializer `Field` subclass which will automatically be used for `ModelSerializer` instances.

## Installation
django-s3-file-field must be used with a compatible Django Storage, which are:
* `S3Boto3Storage` in [django-storages](https://django-storages.readthedocs.io/),
  for [AWS S3](https://aws.amazon.com/s3/)
* `MinioStorage` or `MinioMediaStorage` in [django-minio-storage](https://django-minio-storage.readthedocs.io/),
  for [MinIO](https://min.io/)

After the appropriate Storage is installed and configured, install django-s3-file-field, using the
corresponding extra:
```bash
pip install django-s3-file-field[boto3]
```
or
```bash
pip install django-s3-file-field[minio]
```

Enable django-s3-file-field as an installed Django app:
```python
# settings.py
INSTALLED_APPS = [
    ...,
    's3_file_field',
]
```

Add django-s3-file-field's URLconf to the root URLconf; the path prefix (`'api/s3-upload/'`)
can be changed arbitrarily as desired:
```python
# urls.py
from django.urls import include, path

urlpatterns = [
    ...,
    path('api/s3-upload/', include('s3_file_field.urls')),
]
```

## Usage
For all usage, define an `S3FileField` on a Django `Model`, instead of a `FileField`:
```python
from django.db import models
from s3_file_field import S3FileField

class Resource(models.Model):
    blob = S3FileField()
```

### Django Forms
When defining a
[Django `ModelForm`](https://docs.djangoproject.com/en/4.2/topics/forms/modelforms/),
the appropriate Form `Field` will be automatically used:
```python
from django.forms import ModelForm
from .models import Resource

class ResourceForm(ModelForm):
    class Meta:
        model = Resource
        fields = ['blob']
```

Forms using django-s3-file-field include additional
[assets](https://docs.djangoproject.com/en/4.2/topics/forms/media/), which it's essential to render
along with the Form. Typically, this can be done in any Form-containing Template as:
```
<head>
  {# Assuming the Form is availible in context as "form" #}
  {{ form.media }}
</head>
```

### Django Rest Framework
When defining a
[Django Rest Framework `ModelSerializer`](https://www.django-rest-framework.org/api-guide/serializers/#modelserializer),
the appropriate Serializer `Field` will be automatically used:
```python
from rest_framework import serializers
from .models import Resource

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['blob']
```

Clients interacting with these RESTful APIs will need to use a corresponding django-s3-file-field
client library. Client libraries (and associated documentation) are available for:
* [Python](python-client/README.md)
* [Javascript / TypeScript](javascript-client/README.md)

### Pytest
When installed, django-s3-file-field makes several
[Pytest fixtures](https://docs.pytest.org/en/latest/explanation/fixtures.html) automatically
available for use.

The `s3ff_field_value` fixture will return a valid input value for Django `ModelForm` or
Django Rest Framework `ModelSerializer` subclasses:
```python
from .forms import ResourceForm

def test_resource_form(s3ff_field_value: str) -> None:
    form = ResourceForm(data={'blob': s3ff_field_value})
    assert form.is_valid()
```

Alternatively, the `s3ff_field_value_factory` fixture transforms a `File` object into a valid input
value (for Django `ModelForm` or Django Rest Framework `ModelSerializer` subclasses), providing
more control over the uploaded file:
```python
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

def test_resource_create(s3ff_field_value_factory):
    client = APIClient()
    stored_file = default_storage.open('some_existing_file.txt')
    s3ff_field_value = s3ff_field_value_factory(stored_file)
    resp = client.post('/resource', data={'blob': s3ff_field_value})
    assert resp.status_code == 201
```
