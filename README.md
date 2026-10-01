# django-s3-file-field
[![PyPI](https://img.shields.io/pypi/v/django-s3-file-field)](https://pypi.org/project/django-s3-file-field/)

django-s3-file-field is a Django library for uploading files directly to
[AWS S3](https://aws.amazon.com/s3/) or [MinIO](https://min.io/) Storage from HTTP clients
(browsers, CLIs, etc.), using signed upload URLs issued by Django.

## Benefits
Uploading a file through Django is expensive. Django must receive the entire file before the view
even runs, buffering it in memory or on disk. With the default (synchronous, pre-fork) workers of
WSGI servers such as [Gunicorn](https://gunicorn.org/design/), each worker handles one request at a
time. While a buffering reverse proxy (which Gunicorn requires in production) shields the worker
from waiting on a slow client, it still occupies machine resources to buffer the file. Worse, after
receiving a file, a Django application typically must itself upload that content to the storage
backend. A large file can occupy a worker for a relatively long time, and a few concurrent uploads
can exhaust the available workers. Platforms with strict request timeouts, like
[Heroku](https://devcenter.heroku.com/articles/request-timeout), may cut a transfer off entirely.

django-s3-file-field avoids this by having clients upload file content directly to the storage
backend. On the Django side, django-s3-file-field itself serves the few fast requests which
authorize and finalize each upload, regardless of the file's size. After an upload completes, the
file is referenced by the `Model` instance as usual.

## Scope
The principal API of django-s3-file-field is the `S3FileField`, which is a subclass of
[Django's `FileField`](https://docs.djangoproject.com/en/6.1/ref/models/fields/#filefield).
django-s3-file-field does not affect any operations other than uploading from external HTTP
clients; for all other file operations (downloading, uploading from the Python API, etc.), refer to
[Django's file management documentation](https://docs.djangoproject.com/en/6.1/topics/files/).

## Installation
django-s3-file-field must be used with a compatible Django Storage, which are:
* `S3Storage` in [django-storages](https://django-storages.readthedocs.io/),
  for [AWS S3](https://aws.amazon.com/s3/)
  * This must be explicitly configured (the defaults are insufficient) to use
    [Signature Version 4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html):
    ```python
    # settings.py
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    ```
* `MinioStorage` or `MinioMediaStorage` in [django-minio-storage](https://django-minio-storage.readthedocs.io/),
  for [MinIO](https://min.io/)

After the appropriate Storage is installed and configured, install django-s3-file-field, using the
corresponding extra:
```bash
pip install "django-s3-file-field[s3]"
```
or
```bash
pip install "django-s3-file-field[minio]"
```

Enable django-s3-file-field as an installed Django app:
```python
# settings.py
INSTALLED_APPS = [
    ...,
    "s3_file_field",
]
```

Add django-s3-file-field's URLconf to the root URLconf; the path prefix (`"api/s3-upload/"`)
can be changed arbitrarily as desired:
```python
# urls.py
from django.urls import include, path

urlpatterns = [
    ...,
    path("api/s3-upload/", include("s3_file_field.urls")),
]
```

## Usage
django-s3-file-field supports both the creation and modification (by overwrite) of
`S3FileField`-containing `Model` instances, in either of two usage patterns:
* server-rendered views (including the Django admin), via the Django Forms API, where Django
  renders the upload widget and processes its submission;
* RESTful APIs, via Django Rest Framework's Serializer API, where the client uploads and submits
  the result itself.

The `Model` definition is common to both usage patterns.

The same browser-side upload widget provides a GUI for either usage pattern. The widget inherits
its font and colors from the surrounding page, and is explicitly compatible with the themes of both
the [DaisyUI](https://daisyui.com/) and [Vuetify](https://vuetifyjs.com/) CSS frameworks.

### Models
For all usage, define an `S3FileField` on a Django `Model`, instead of a `FileField`:
```python
from django.db import models
from s3_file_field import S3FileField


class Resource(models.Model):
    blob = S3FileField()
```

#### Limiting file size
A maximum file size (in bytes) may be set on each `S3FileField`:
```python
class Resource(models.Model):
    blob = S3FileField(max_size=100 * 1024 * 1024)  # 100 MiB
```

A default for all `S3FileField`s which don't set their own `max_size` may be set globally:
```python
# settings.py
S3_FILE_FIELD_MAX_SIZE = 100 * 1024 * 1024  # 100 MiB
```

When neither is set, the limit is the storage backend's own maximum upload size
(5 TB on AWS S3).

### Django Forms
In this usage pattern, everything is handled by the Form layer, as with a Django `FileField`: the
Form renders the upload widget, which performs the upload in the browser; validates the submitted
value; redisplays it when another field is invalid; keeps, replaces or clears an existing file on
edit; and assigns the result to the `Model`. The `<s3-file-input>` element (described under REST
APIs) is never manipulated directly.

When defining a
[Django `ModelForm`](https://docs.djangoproject.com/en/6.1/topics/forms/modelforms/),
the appropriate Form `Field` will be automatically used:
```python
from django.forms import ModelForm
from .models import Resource


class ResourceForm(ModelForm):
    class Meta:
        model = Resource
        fields = ["blob"]
```

Forms using django-s3-file-field include additional
[assets](https://docs.djangoproject.com/en/6.1/topics/forms/media/), which it's essential to render
along with the Form. Typically, this can be done in any Form-containing Template as:
```
<head>
  {# Assuming the Form is available in context as "form" #}
  {{ form.media }}
</head>
```

When declaring the field on a plain (non-model) `Form`, use an `S3FormFileField`, whose required
argument `model_field` references the model field it submits to:
```python
from django.forms import Form
from s3_file_field.forms import S3FormFileField
from .models import Resource


class ResourceForm(Form):
    blob = S3FormFileField(model_field=Resource._meta.get_field("blob"))
```

### REST APIs
In this usage pattern, the application declares its API with a Django Rest Framework Serializer,
using an `S3FileSerializerField` to provide an interface to an `S3FileField`. The application's
client then uploads files with an `<s3-file-input>` element (in a browser) or client library (in
JavaScript or Python), and submits the resulting values to the application's API.

#### Django Rest Framework
When defining a
[Django Rest Framework `ModelSerializer`](https://www.django-rest-framework.org/api-guide/serializers/#modelserializer),
the appropriate Serializer Field will be automatically used:
```python
from rest_framework import serializers
from .models import Resource


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ["blob"]
```

When declaring the field on a plain (non-model) `Serializer`, use an `S3FileSerializerField`, whose
required argument `model_field` references the model field it submits to:
```python
from rest_framework import serializers
from s3_file_field.rest_framework import S3FileSerializerField
from .models import Resource


class ResourceSerializer(serializers.Serializer):
    blob = S3FileSerializerField(model_field=Resource._meta.get_field("blob"))
```

#### Browser clients: the `<s3-file-input>` element
In a web browser, a file is uploaded with the `<s3-file-input>` element: a custom element which
presents a file picker, uploads the chosen file to the storage backend, and provides the resulting
value for the application to submit. It is the same element which the Form layer renders as its
widget.

The element is loaded by including its assets (where `/static/` is
[Django's `STATIC_URL`](https://docs.djangoproject.com/en/6.1/ref/settings/#std-setting-STATIC_URL)):
```html
<link rel="stylesheet" href="/static/s3_file_field/s3-file-input.css">
<script type="module" src="/static/s3_file_field/s3-file-input.js"></script>
```

It is configured with the following HTML attributes, which are also available as JavaScript
properties:

| Attribute | Property | Type | Meaning |
|---|---|---|---|
| `base-url` | `baseUrl` | `string` | The URL path at which django-s3-file-field's URLconf is included (e.g. `/api/s3-upload/`) |
| `field-id` | `fieldId` | `string` | The identifier of the `S3FileField` to upload to, as `<app_label>.<Model>.<field>` |
| `max-size` | `maxSize` | `number` | (optional) The maximum file size, checked before uploading; omit when none is configured |
| `existing-url` | `existingUrl` | `string` | (optional) The URL of the existing file stored in this field (i.e. the output of the serializer) |
| `disabled` | `disabled` | `boolean` | (optional) Whether the field is disabled; the field is also disabled by a disabled ancestor `<fieldset>` |
| `name` | `name` | `string` | (optional) When within a form, the name of the submitted field |
| `required` | `required` | `boolean` | (optional) When within a form, whether a file is required; keeping an existing file satisfies this |

When placed within a `<form>`, an `<s3-file-input>` submits its value under its `name` and reports
validity like a native input, so a missing `required` file or an upload in progress blocks form
submission.

To submit the element's value to a RESTful API, read the `value` property of the element.
The element will fire an `input` event when the `value` property is changed by user input.

##### Vue.js examples
The element may be bound with Vue.js's `v-model`, or placed in a form, whose data then includes
its value.

For example, creating the hypothetical `Resource`:
```vue
<script setup>
// Vue should be configured to resolve "s3-file-input" as a custom element, rather than a component
// (via "compilerOptions.isCustomElement"):
// https://vuejs.org/guide/extras/web-components.html#skipping-component-resolution
import { ref } from "vue";

// The element's value
const blob = ref("");

async function save() {
  await fetch("/api/resources/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blob: blob.value }),
  });
}
</script>

<template>
  <s3-file-input
    v-model="blob"
    base-url="/api/s3-upload/"
    field-id="myapp.Resource.blob"
  ></s3-file-input>
  <button @click="save">Save</button>
</template>
```

Or, updating an existing `Resource`:
```vue
<script setup>
import { onMounted, ref } from "vue";

const props = defineProps({ id: Number });
// The API represents the file as its URL
const resource = ref({ blob: "" });

onMounted(async () => {
  resource.value = await (await fetch(`/api/resources/${props.id}/`)).json();
});

async function save(event) {
  // The <s3-file-input> knows how to contribute its value to FormData.
  // Note, it will be deliberately absent if the existing file is kept,
  // which aligns with PATCH only submitting changed fields.
  await fetch(`/api/resources/${props.id}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.fromEntries(new FormData(event.target))),
  });
}
</script>

<template>
  <form @submit.prevent="save">
    <s3-file-input
      name="blob"
      base-url="/api/s3-upload/"
      field-id="myapp.Resource.blob"
      required
      :existing-url="resource.blob"
    ></s3-file-input>
    <button>Save</button>
  </form>
</template>
```

#### JavaScript client library
A frontend which doesn't use the `<s3-file-input>` element (as when the file comes from somewhere
other than a file input, or the UI is entirely custom) may upload directly with the
[JavaScript / TypeScript client library](javascript-client/README.md).

#### Python client library
Scripts and other non-browser clients may upload with the
[Python client library](python-client/README.md).

### Pytest
When installed, django-s3-file-field makes a
[Pytest fixture](https://docs.pytest.org/en/latest/explanation/fixtures.html) automatically
available for use.

The `s3ff_field_value_factory` fixture transforms a stored `File` object into a valid input value
for Django `ModelForm` or Django Rest Framework `ModelSerializer` subclasses. Since a field value
is bound to the `S3FileField` it is uploaded to, the target model field must be passed too:
```python
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from .models import Resource


def test_resource_create(s3ff_field_value_factory):
    client = APIClient()
    stored_file = default_storage.open("some_existing_file.txt")
    s3ff_field_value = s3ff_field_value_factory(stored_file, Resource._meta.get_field("blob"))
    resp = client.post("/resource", data={"blob": s3ff_field_value})
    assert resp.status_code == 201
```
