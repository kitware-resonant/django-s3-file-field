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


# The submitted value which clears an existing file. Otherwise, a submitted value is a signed
# FieldValue (which this can never be mistaken for), and an empty or omitted value keeps any
# existing file. Kept identical in the widget's JavaScript.
CLEAR_VALUE = "s3ff:clear"


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

        # "existing-url" is best-effort display information, which the widget names the file by
        if isinstance(value, str) and value:
            # A pending FieldValue shouldn't provide a URL (the upload is not yet validated, so it
            # shouldn't be served), but its storage key still names it
            try:
                parsed = FieldValue.model_validate(value)
            except PydanticValidationError:
                # The value is still rendered, but will be rejected if resubmitted
                pass
            else:
                attrs["existing-url"] = parsed.object_key
        elif isinstance(value, FieldFile) and value:
            # A saved FieldFile provides its URL, but only if it's not falsey (as it is when
            # editing an empty optional field)
            attrs["existing-url"] = value.url
        # A cleared existing file (on redisplay) has no URL available, and needn't show any

        return super().get_context(name, value, attrs)

    @override
    def format_value(self, value: FieldFile | str | Literal[False] | None) -> str | None:
        """
        Return the value as it should be provided to the widget template.

        The "value" is rendered as it's to be resubmitted, which mirrors "value_from_datadict".
        """
        if value is False:
            # A clear of an existing file (on redisplay)
            return CLEAR_VALUE
        if isinstance(value, str) and value:
            # A pending FieldValue (on redisplay)
            return value
        # An initial FieldFile is conveyed via "existing-url" instead (see "get_context"), as
        # keeping it is expressed by submitting nothing; an empty value is equivalent, so it's not
        # rendered either
        return None

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
            if value == CLEAR_VALUE:
                # Clear any existing value
                return False
            if not value:
                # An empty value is equivalent to an omitted one: keep any existing value
                return None
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
        # An empty value is equivalent to an omitted one
        return (not data.get(name)) and (name not in files)
