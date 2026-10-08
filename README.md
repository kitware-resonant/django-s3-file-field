# django-s3-file-field
[![PyPI](https://img.shields.io/pypi/v/django-s3-file-field)](https://pypi.org/project/django-s3-file-field/)

django-s3-file-field is a Django library for uploading files directly to
[AWS S3](https://aws.amazon.com/s3/) or [MinIO](https://min.io/) object storage from HTTP clients
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
file is referenced by the model instance as usual.

## Scope
The principal API of django-s3-file-field is the `S3FileField`, which is a subclass of
[Django's `FileField`](https://docs.djangoproject.com/en/stable/ref/models/fields/#filefield).
django-s3-file-field does not affect any operations other than uploading from external HTTP
clients; for all other file operations (downloading, uploading from the Python API, etc.), refer to
[Django's file management documentation](https://docs.djangoproject.com/en/stable/topics/files/).

## Installation
django-s3-file-field must be used with a compatible storage backend, one of:
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

After the storage backend is installed and configured, install django-s3-file-field, using the
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
model instances with an `S3FileField`, in either of two usage patterns:
* server-rendered views (including the Django admin), via Django's forms API, where Django
  renders the upload widget and processes its submission;
* RESTful APIs, via Django REST framework's serializer API, where the client uploads and submits
  the result itself.

The model definition is common to both usage patterns.

The same browser-side upload widget provides a GUI for either usage pattern. The widget inherits
its font and colors from the surrounding page, and is explicitly compatible with the themes of both
the [DaisyUI](https://daisyui.com/) and [Vuetify](https://vuetifyjs.com/) CSS frameworks.

### Models
For all usage, define an `S3FileField` on a Django model, instead of a `FileField`:
```python
from django.db import models
from s3_file_field import S3FileField


class Resource(models.Model):
    blob = S3FileField()
```

#### Limiting file size
A maximum file size (in bytes) may be set on each `S3FileField`:
```python
from django.db import models
from s3_file_field import S3FileField


class Resource(models.Model):
    blob = S3FileField(max_size=100 * 1024 * 1024)  # 100 MiB
```

A default for all `S3FileField` instances which don't set their own `max_size` may be set globally:
```python
# settings.py
S3_FILE_FIELD_MAX_SIZE = 100 * 1024 * 1024  # 100 MiB
```

When neither is set, the limit is the storage backend's own maximum upload size
(5 TB on AWS S3).

#### Model validators
[Validators](https://docs.djangoproject.com/en/stable/ref/validators/) may be set on an
`S3FileField`. As with any model field, they run when a model instance is validated with
[`full_clean()`](https://docs.djangoproject.com/en/stable/ref/models/instances/#django.db.models.Model.full_clean).

For example:
```python
from django.core.validators import FileExtensionValidator
from django.db import models
from s3_file_field import S3FileField


class Resource(models.Model):
    blob = S3FileField(validators=[FileExtensionValidator(allowed_extensions=["pdf"])])
```

Custom validators may also be defined, receiving the uploaded file as
[a `File`-like value](https://docs.djangoproject.com/en/stable/ref/files/file/#the-file-class).
The value includes attributes for `name` and `size`, along with methods for reading the file
content (though this downloads it from the storage backend). A validator is only called when a file
is present; as with any model field, an empty or cleared field skips the validators entirely.

For example:
```python
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from s3_file_field import S3FileField


def validate_pdf(value: File) -> None:
    with value.open() as stream:
        if stream.read(5) != b"%PDF-":
            raise ValidationError("Not a PDF file.", code="invalid_type")


class Resource(models.Model):
    blob = S3FileField(validators=[validate_pdf])
```

Note, validators run after the file has already been fully uploaded to the storage backend, so
rejecting it only prevents a reference to the file from being saved; the uploaded file itself
remains in the storage backend.

### Django forms
In this usage pattern, everything is handled by the form layer, as with a Django `FileField`: the
form renders the upload widget, which performs the upload in the browser; validates the submitted
value; redisplays it when another field is invalid; keeps, replaces or clears an existing file on
edit; and assigns the result to the model instance. The `<s3-file-input>` element (described under
REST APIs) is never manipulated directly.

When defining a
[Django `ModelForm`](https://docs.djangoproject.com/en/stable/topics/forms/modelforms/),
the appropriate form field will be automatically used:
```python
from django.forms import ModelForm
from .models import Resource


class ResourceForm(ModelForm):
    class Meta:
        model = Resource
        fields = ["blob"]
```

Forms using django-s3-file-field include additional
[assets](https://docs.djangoproject.com/en/stable/topics/forms/media/), which it's essential to render
along with the form. Typically, this can be done in any form-containing template as:
```
<head>
  {# Assuming the form is available in context as "form" #}
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

#### Form validation
A `ModelForm` will run all validators declared on the model field.

Additionally, [Form validation](https://docs.djangoproject.com/en/stable/ref/forms/validation/)
is supported. This provides access to the form's other fields (within `clean()`) and the
`instance` (for a `ModelForm`), which a model validator can't see.

Note, if the field is optional (the model sets `blank=True`), the `clean_<field>` method may also
receive `None` or `False` values, indicating empty (no file at all) or cleared (existing file about
to be removed) states, respectively. In all cases of editing an existing instance, a kept file
(where the user didn't modify the field) will re-run form validation, with a `File`-like value of
the existing file.

For example:
```python
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.db.models.fields.files import FieldFile
from django.forms import ModelForm
from .models import Resource


class ResourceForm(ModelForm):
    def clean_blob(self) -> File:
        blob: File = self.cleaned_data["blob"]
        existing_blob: FieldFile = self.instance.blob
        if not existing_blob:
            # The field is required, so this must be a new instance
            return blob

        blob_suffix = PurePosixPath(blob.name).suffix
        existing_blob_suffix = PurePosixPath(existing_blob.name).suffix
        # Once a file is saved, it can be replaced, but only with the same extension
        if blob_suffix != existing_blob_suffix:
            raise ValidationError("Cannot change the file's extension.", code="invalid")

        return blob

    class Meta:
        model = Resource
        fields = ["blob"]
```

### REST APIs
In this usage pattern, the application declares its API with a Django REST framework serializer,
using an `S3FileSerializerField` to provide an interface to an `S3FileField`. The application's
client then uploads files with an `<s3-file-input>` element (in a browser) or client library (in
JavaScript or Python), and submits the resulting values to the application's API.

#### Django REST framework
When defining a
[Django REST framework `ModelSerializer`](https://www.django-rest-framework.org/api-guide/serializers/#modelserializer),
the appropriate serializer field will be automatically used:
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

##### Serializer validation
A `ModelSerializer` will run all validators declared on the model field.

Additionally,
[serializer validation](https://www.django-rest-framework.org/api-guide/serializers/#validation)
is supported. This provides access to the request (within `self.context`), the serializer's other
fields (within `validate()`), and the `instance` (for a `ModelSerializer`, when updating), which a
model validator can't see.

Note, if the field is optional (the model sets `blank=True`), the `validate_<field>` method may also
receive a `None` value, indicating a cleared (existing file about to be removed) state. In all cases
of partially updating an existing instance, a kept file (where the client omitted the field or
submitted an empty value) will skip serializer validation entirely.

For example:
```python
from django.core.files import File
from rest_framework import serializers
from rest_framework.request import Request
from .models import Resource


class ResourceSerializer(serializers.ModelSerializer):
    def validate_blob(self, value: File) -> File:
        request: Request = self.context["request"]
        if not request.user.is_staff and value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "Non-staff uploads are limited to 10 MiB.", code="too_large"
            )

        return value

    class Meta:
        model = Resource
        fields = ["blob"]
```

#### Browser clients: the `<s3-file-input>` element
In a web browser, a file is uploaded with the `<s3-file-input>` element: a custom element which
presents a file picker, uploads the chosen file to the storage backend, and provides the resulting
value for the application to submit. It is the same element which the form layer renders as its
widget.

The element is loaded by including its assets (where `/static/` is
[Django's `STATIC_URL`](https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-STATIC_URL)):
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

Vue.js should be configured to
[resolve `s3-file-input` as a custom element](https://vuejs.org/guide/extras/web-components.html#skipping-component-resolution),
rather than as a component (via `compilerOptions.isCustomElement`).

For example, creating the hypothetical `Resource`:
```vue
<script setup>
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

### pytest
When installed, django-s3-file-field makes a
[pytest fixture](https://docs.pytest.org/en/latest/explanation/fixtures.html) automatically
available for use.

The `s3ff_field_value_factory` fixture transforms a stored `File` object into a valid input value
for Django `ModelForm` or Django REST framework `ModelSerializer` subclasses. Since a field value
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
