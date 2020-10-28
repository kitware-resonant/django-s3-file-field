from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import pytest
from test_app.forms import ResourceForm

from s3_file_field.forms import S3FormFileField


@pytest.fixture
def field_value(storage_object_key):
    return signing.dumps(
        {
            'object_key': storage_object_key,
            # TODO: Compute this dynamically
            'file_size': len(b'test content'),
        }
    )


@pytest.fixture()
def storage_object_key() -> str:
    """Return the key to an object saved directly into Storage."""
    # TODO: random key
    key = 'test_key'
    default_storage.save(key, ContentFile(b'test content'))
    return key


def test_form_field_type():
    form = ResourceForm()
    assert isinstance(form.fields['blob'], S3FormFileField)


def test_form_missing(storage_object_key):
    form = ResourceForm(data={})
    assert not form.is_valid()


def test_form_empty(storage_object_key):
    form = ResourceForm(data={'blob': ''})
    assert not form.is_valid()


def test_form_invalid(storage_object_key):
    form = ResourceForm(data={'blob': 'invalid:field_value'})
    assert not form.is_valid()


def test_form_validation(field_value):
    form = ResourceForm(data={'blob': field_value})
    assert form.is_valid()


def test_form_instance(field_value):
    form = ResourceForm(data={'blob': field_value})

    # full_clean has the side effect of populating instance
    form.full_clean()
    resource = form.instance

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b'test content'


@pytest.mark.django_db
def test_form_instance_saved(field_value):
    form = ResourceForm(data={'blob': field_value})

    resource = form.save()
    resource.refresh_from_db()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b'test content'
