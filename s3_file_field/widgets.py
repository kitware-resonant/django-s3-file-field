from __future__ import annotations

import functools
import posixpath
from typing import TYPE_CHECKING, Any, Literal, override

from django.db.models.fields.files import FieldFile
from django.forms import Script, Widget
from django.urls import get_script_prefix, get_urlconf, reverse
from pydantic import ValidationError as PydanticValidationError

from ._schemas import FieldValue

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.core.files.uploadedfile import UploadedFile
    from django.utils.datastructures import MultiValueDict


@functools.lru_cache
def _get_base_url(urlconf: str | None, _script_prefix: str) -> str:
    # include these arguments to avoid cache pollution, since Django is allowed to change
    # urlconf per-request and script_prefix may be initially incorrect:
    # https://code.djangoproject.com/ticket/36653
    initiate_url = reverse("s3_file_field:initiate", urlconf=urlconf)
    complete_url = reverse("s3_file_field:complete", urlconf=urlconf)
    # Use posixpath to always parse URL paths with forward slashes
    return posixpath.commonpath([initiate_url, complete_url])


def get_base_url() -> str:
    return _get_base_url(get_urlconf(), get_script_prefix())


class S3FileInput(Widget):
    """Widget rendering an S3FormFileField as a "s3-file-input" custom element."""

    template_name = "s3_file_field/widgets/s3_file_input.html"

    class Media:
        css = {
            "all": ["s3_file_field/s3-file-input.css"],
        }
        js = [
            Script("s3_file_field/s3-file-input.js", type="module"),
        ]

    @override
    def use_required_attribute(self, initial: FieldFile | None) -> bool:
        """Return whether to render the "required" HTML attribute on the widget."""
        # As with file inputs, don't render "required" when there's an initial value,
        # since keeping it is expressed by submitting nothing.
        return super().use_required_attribute(initial) and not initial

    @override
    def get_context(
        self,
        name: str,
        value: FieldFile | str | Literal[False] | None,
        attrs: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Return the template context for rendering this widget, resolved at render time."""
        # Copy, to avoid mutating the caller's dict
        attrs = dict(attrs or {})

        # The base URL cannot be determined at the time the widget is instantiated
        # (during app startup), as it requires URLconf resolution
        attrs["base-url"] = get_base_url()

        # "file-name" and "file-url" are best-effort display information
        if isinstance(value, str) and value:
            # A pending FieldValue shouldn't provide a URL (the upload is not yet validated, so it
            # shouldn't be served), but it still has a usable file name
            try:
                parsed = FieldValue.model_validate(value)
            except PydanticValidationError:
                # The value is still rendered, but will be rejected if resubmitted
                pass
            else:
                attrs["file-name"] = parsed.object_key
        elif isinstance(value, FieldFile) and value:
            # A saved FieldFile provides both, but only if it's not falsey (as it is when editing
            # an empty optional field)
            attrs["file-name"] = value.name
            attrs["file-url"] = value.url
        elif value is False:
            # A cleared existing file (on redisplay) is conveyed as a state, so the clear
            # survives; its file info is no longer available, and needn't be shown anyway
            attrs["cleared"] = True

        return super().get_context(name, value, attrs)

    @override
    def format_value(self, value: FieldFile | str | Literal[False] | None) -> str | None:
        """Return the value as it should be provided to the widget template."""
        # Only a pending FieldValue string is rendered as the "value" (its presence determines
        # the pending state); an initial FieldFile is conveyed via "file-name" and "file-url"
        # and a cleared one via "cleared" (see get_context).
        return value if isinstance(value, str) and value else None

    @override
    def value_from_datadict(
        self, data: Mapping[str, str], files: MultiValueDict[str, UploadedFile[Any]], name: str
    ) -> str | Literal[False] | UploadedFile[Any] | None:
        """
        Return this widget's value, extracted from the submitted form data.

        This is called before "S3FormFileField.to_python".
        """
        if name in data:
            value = data[name]
            if not value:
                # An explicit empty value signals to clear any existing value, as opposed to
                # None (from an omitted entry), which signals to keep it.
                return False
            # Expected to be a signed FieldValue string;
            # S3FormFileField.to_python verifies and converts it
            return value
        if name in files:
            # A direct file upload, which S3FormFileField.to_python will refuse
            return files.get(name)
        return None

    @override
    def value_omitted_from_data(
        self, data: Mapping[str, str], files: MultiValueDict[str, UploadedFile[Any]], name: str
    ) -> bool:
        """Return whether this widget's value is omitted from the submitted form data."""
        return (name not in data) and (name not in files)
