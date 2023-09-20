import pytest

from s3_file_field.forms import S3FormFileField

from test_app.forms import ResourceForm


def test_form_field_type() -> None:
    form = ResourceForm()
    assert isinstance(form.fields["blob"], S3FormFileField)


def test_form_missing() -> None:
    form = ResourceForm(data={})
    assert not form.is_valid()


def test_form_empty() -> None:
    form = ResourceForm(data={"blob": ""})
    assert not form.is_valid()


def test_form_invalid() -> None:
    form = ResourceForm(data={"blob": "invalid:field_value"})
    assert not form.is_valid()


def test_form_validation(s3ff_field_value: str) -> None:
    form = ResourceForm(data={"blob": s3ff_field_value})
    assert form.is_valid()


def test_form_instance(s3ff_field_value: str) -> None:
    form = ResourceForm(data={"blob": s3ff_field_value})

    # full_clean has the side effect of populating instance
    form.full_clean()
    resource = form.instance

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"


@pytest.mark.django_db()
def test_form_instance_saved(s3ff_field_value: str) -> None:
    form = ResourceForm(data={"blob": s3ff_field_value})

    resource = form.save()
    resource.refresh_from_db()

    with resource.blob.open() as blob_stream:
        assert blob_stream.read() == b"test content"
