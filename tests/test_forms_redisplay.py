from __future__ import annotations

from typing import cast

from factories import (
    FieldValueFactory,
    MultiResourceFactory,
    OptionalResourceFactory,
    ResourceFactory,
)
from form_inspection import rendered_attrs
from fuzzy import FUZZY_INT, Fuzzy
from test_app.forms import (
    DisabledResourceForm,
    MultiResourceForm,
    OptionalResourceForm,
    ResourceForm,
)
from test_app.models import MultiResource


def test_form_redisplay_create() -> None:
    """A completed upload is redisplayed when validation fails elsewhere on a create form."""
    field_value = FieldValueFactory.build(
        field_model=MultiResource, field_name="optional_blob", object_key="key/file.txt"
    )
    field_value_str = cast("str", field_value.model_dump())
    # "blob" is missing, so the form is invalid
    form = MultiResourceForm(data={"optional_blob": field_value_str})

    assert not form.is_valid()
    # A pending upload is not yet validated, so no "file-url" is rendered to serve it
    assert rendered_attrs(form["optional_blob"]) == {
        "name": "optional_blob",
        "id": "id_optional_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.MultiResource.optional_blob",
        "max-size": FUZZY_INT,
        "value": field_value_str,
        "file-name": "key/file.txt",
    }


def test_form_redisplay_create_clear() -> None:
    """An abnormal clear (with no existing file) is refused, and redisplayed as nothing."""
    form = ResourceForm(data={"blob": ""})

    assert not form.is_valid()
    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.Resource.blob",
        "max-size": FUZZY_INT,
        "required": None,
        "aria-invalid": "true",
        "aria-describedby": "id_blob_error",
    }


def test_form_redisplay_create_invalid() -> None:
    """An unparseable pending value is still redisplayed, escaped and without any file info."""
    # A hostile value, to also prove that it's escaped
    invalid_value = '" onfocus="alert(1)'
    form = ResourceForm(data={"blob": invalid_value})

    assert not form.is_valid()
    # parse_html unescapes, so equality proves the value was escaped and round-tripped, rather
    # than injecting an "onfocus" attribute
    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.Resource.blob",
        "max-size": FUZZY_INT,
        "required": None,
        "value": invalid_value,
        "aria-invalid": "true",
        "aria-describedby": "id_blob_error",
    }


def test_form_redisplay_edit() -> None:
    """An untouched existing file is redisplayed when validation fails elsewhere on an edit form."""
    instance = MultiResourceFactory.build(blob="", optional_blob="key/file.txt")
    # "blob" is missing, so the form is invalid
    form = MultiResourceForm(data={}, instance=instance)

    assert not form.is_valid()
    assert rendered_attrs(form["optional_blob"]) == {
        "name": "optional_blob",
        "id": "id_optional_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.MultiResource.optional_blob",
        "max-size": FUZZY_INT,
        "file-name": "key/file.txt",
        "file-url": Fuzzy(r"^https?://.*/key/file\.txt"),
    }


def test_form_redisplay_edit_clear() -> None:
    """A clear of an existing file survives when validation fails elsewhere on an edit form."""
    instance = MultiResourceFactory.build(blob="", optional_blob="key/file.txt")
    # "blob" is missing, so the form is invalid
    form = MultiResourceForm(data={"optional_blob": ""}, instance=instance)

    assert not form.is_valid()
    # The cleared file's info is no longer available
    assert rendered_attrs(form["optional_blob"]) == {
        "name": "optional_blob",
        "id": "id_optional_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.MultiResource.optional_blob",
        "max-size": FUZZY_INT,
        "cleared": None,
    }


def test_form_redisplay_edit_clear_required() -> None:
    """A refused clear of a required field's existing file is still redisplayed as cleared."""
    instance = ResourceFactory.build(blob="key/file.txt")
    form = ResourceForm(data={"blob": ""}, instance=instance)

    assert not form.is_valid()
    # The user may then keep the existing file, or upload a replacement
    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.Resource.blob",
        "max-size": FUZZY_INT,
        "cleared": None,
        "aria-invalid": "true",
        "aria-describedby": "id_blob_error",
    }


def test_form_redisplay_edit_invalid() -> None:
    """An unparseable pending value eclipses an existing file's info on redisplay."""
    instance = OptionalResourceFactory.build(blob="key/file.txt")
    form = OptionalResourceForm(data={"blob": "invalid:field_value"}, instance=instance)

    assert not form.is_valid()
    # The pending value alone determines the represented file, so the existing file's info
    # is not rendered
    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.OptionalResource.blob",
        "max-size": FUZZY_INT,
        "value": "invalid:field_value",
        "aria-invalid": "true",
        "aria-describedby": "id_blob_error",
    }


def test_form_redisplay_edit_disabled() -> None:
    """A disabled field ignores any submitted value, redisplaying the existing file."""
    instance = ResourceFactory.build(blob="key/file.txt")
    form = DisabledResourceForm(data={"blob": "invalid:field_value"}, instance=instance)

    # The submitted value is not even validated
    assert form.is_valid()
    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.Resource.blob",
        "max-size": FUZZY_INT,
        "disabled": None,
        "file-name": "key/file.txt",
        "file-url": Fuzzy(r"^https?://.*/key/file\.txt"),
    }
