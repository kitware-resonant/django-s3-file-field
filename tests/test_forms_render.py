from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.widgets import AdminFileWidget
from django.db import models

from factories import (
    OptionalResourceFactory,
    ResourceFactory,
)
from form_inspection import rendered_attrs
from fuzzy import FUZZY_INT, Fuzzy
from s3_file_field.forms import S3FormFileField
from s3_file_field.widgets import S3FileInput
from test_app.forms import (
    DisabledResourceForm,
    LimitedResourceForm,
    OptionalResourceForm,
    ResourceForm,
)
from test_app.models import Resource

if TYPE_CHECKING:
    from django.test import RequestFactory


def test_form_field_type() -> None:
    form = ResourceForm()
    assert isinstance(form.fields["blob"], S3FormFileField)


def test_form_widget_type_admin(rf: RequestFactory) -> None:
    """A default ModelAdmin form uses the widget, instead of its usual AdminFileWidget."""
    model_admin = ModelAdmin(Resource, AdminSite())
    admin_form_class = model_admin.get_form(rf.get("/"))
    admin_form = admin_form_class()

    # The form field class is unaffected by the admin, so only the widget can reveal a problem
    assert isinstance(admin_form.fields["blob"].widget, S3FileInput)


def test_form_widget_type_admin_override(rf: RequestFactory) -> None:
    """A ModelAdmin's AdminFileWidget instance override is replaced, keeping its attrs."""

    class OverrideModelAdmin(ModelAdmin[Resource]):
        formfield_overrides = {
            models.FileField: {"widget": AdminFileWidget(attrs={"class": "special"})},
        }

    model_admin = OverrideModelAdmin(Resource, AdminSite())
    admin_form_class = model_admin.get_form(rf.get("/"))
    admin_form = admin_form_class()

    widget = admin_form.fields["blob"].widget
    assert isinstance(widget, S3FileInput)
    assert widget.attrs["class"] == "special"


def test_form_render_create() -> None:
    """A create form renders the field's configuration, with no file info or value."""
    form = ResourceForm()

    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.Resource.blob",
        "max-size": FUZZY_INT,
        "required": None,
    }


def test_form_render_max_size() -> None:
    """The model field's max_size is rendered, for the client to pre-check file sizes."""
    form = LimitedResourceForm()

    assert rendered_attrs(form["blob"])["max-size"] == "10"


def test_form_render_disabled() -> None:
    """A disabled field renders the "disabled" HTML attribute."""
    form = DisabledResourceForm()

    assert "disabled" in rendered_attrs(form["blob"])


def test_form_render_edit() -> None:
    """An edit form renders the existing file's info, which is kept by default."""
    instance = ResourceFactory.build(blob="key/file.txt")
    form = ResourceForm(instance=instance)

    # "required" is not rendered, since keeping the existing file is expressed by submitting
    # nothing; "value" is not rendered for a saved file, as it only persists pending uploads
    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.Resource.blob",
        "max-size": FUZZY_INT,
        "file-name": "key/file.txt",
        "file-url": Fuzzy(r"^https?://.*/key/file\.txt"),
    }


def test_form_render_edit_empty() -> None:
    """An edit form for an instance with an empty optional file renders no file info."""
    form = OptionalResourceForm(instance=OptionalResourceFactory.build(blob=""))

    assert rendered_attrs(form["blob"]) == {
        "name": "blob",
        "id": "id_blob",
        "base-url": "/api/s3ff_test",
        "field-id": "test_app.OptionalResource.blob",
        "max-size": FUZZY_INT,
    }


def test_form_render_edit_empty_required() -> None:
    """An edit form for an instance with an empty required file still renders "required"."""
    form = ResourceForm(instance=ResourceFactory.build(blob=""))

    assert "required" in rendered_attrs(form["blob"])


def test_form_multipart() -> None:
    """The form doesn't need a multipart encoding, since only strings are submitted."""
    assert ResourceForm().is_multipart() is False


def test_widget_media() -> None:
    form = ResourceForm()

    rendered = str(form.media)

    assert (
        '<link href="/static/s3_file_field/s3-file-input.css" media="all" rel="stylesheet">'
    ) in rendered
    assert (
        '<script src="/static/s3_file_field/s3-file-input.js" type="module"></script>'
    ) in rendered
