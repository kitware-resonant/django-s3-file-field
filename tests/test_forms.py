import json

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import pytest
from test_app.forms import ResourceForm

from s3_file_field.forms import S3FormFileField


@pytest.fixture()
def storage_object_key() -> str:
    """Return the key to an object saved directly into Storage."""
    # TODO: random key
    key = 'test_key'
    default_storage.save(key, ContentFile(b'test content'))
    return key


@pytest.mark.django_db
def test_form_field_type():
    form = ResourceForm()
    assert isinstance(form.fields['blob'], S3FormFileField)


def test_form_validation(storage_object_key):
    # TODO: other fields
    data = json.dumps(
        {
            'id': storage_object_key,
            'name': '',
            'size': 12,
            'signature': '',
        }
    )
    form = ResourceForm(data={'blob': data})
    assert form.is_valid()


def test_form_instance(storage_object_key):
    data = json.dumps(
        {
            'id': storage_object_key,
            'name': '',
            'size': 12,
            'signature': '',
        }
    )
    form = ResourceForm(data={'blob': data})

    # full_clean has the side effect of populating instance
    form.full_clean()
    resource = form.instance

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b'test content'


@pytest.mark.django_db
def test_form_instance_saved(storage_object_key):
    data = json.dumps(
        {
            'id': storage_object_key,
            'name': '',
            'size': 12,
            'signature': '',
        }
    )
    form = ResourceForm(data={'blob': data})

    resource = form.save()
    resource.refresh_from_db()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b'test content'


@pytest.mark.parametrize('value', ['', '""', 'null', '{}', json.dumps({'id': ''})])
@pytest.mark.django_db
def test_form_empty(storage_object_key, value):
    form = ResourceForm(data={'blob': value})

    assert not form.is_valid()
