import pytest

from s3_file_field.forms import S3FormFileField
from test_app.forms import ResourceForm


def test_form_field_type():
    form = ResourceForm()
    assert isinstance(form.fields['blob'], S3FormFileField)


def test_form_missing():
    form = ResourceForm(data={})
    assert not form.is_valid()


def test_form_empty():
    form = ResourceForm(data={'blob': ''})
    assert not form.is_valid()


def test_form_invalid():
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
