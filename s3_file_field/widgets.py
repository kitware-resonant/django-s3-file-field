from __future__ import annotations

import functools
import posixpath
from typing import TYPE_CHECKING, Any, override

from django.forms import ClearableFileInput
from django.forms.widgets import FILE_INPUT_CONTRADICTION, CheckboxInput
from django.urls import reverse

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.core.files.uploadedfile import UploadedFile
    from django.utils.datastructures import MultiValueDict


@functools.lru_cache(maxsize=1)
def get_base_url() -> str:
    initiate_url = reverse("s3_file_field:initiate")
    complete_url = reverse("s3_file_field:complete")
    # Use posixpath to always parse URL paths with forward slashes
    return posixpath.commonpath([initiate_url, complete_url])


class S3FileInput(ClearableFileInput):
    """Widget to render the S3 File Input."""

    class Media:
        js = ["s3_file_field/widget.js"]
        css = {"all": ["s3_file_field/widget.css"]}

    @override
    def get_context(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        # The base URL cannot be determined at the time the widget is instantiated
        # (when S3FormFileField.widget_attrs is called).
        # Additionally, because this method is called on a deep copy of the widget each
        # time it's rendered, this assignment to an instance variable is not persisted.
        self.attrs["data-s3fileinput"] = get_base_url()
        return super().get_context(*args, **kwargs)

    @override
    def value_from_datadict(
        self, data: Mapping[str, Any], files: MultiValueDict[str, UploadedFile[Any]], name: str
    ) -> Any:
        if name in data:
            # The raw value, expected to be a signed FieldValue string;
            # S3FormFileField.to_python verifies and converts it
            upload: Any = data[name]
        elif name in files:
            # A direct file upload, which S3FormFileField.to_python will refuse
            upload = files.get(name)
        else:
            upload = None

        if not self.is_required and CheckboxInput().value_from_datadict(
            data, files, self.clear_checkbox_name(name)
        ):
            if upload:
                # If the user contradicts themselves (uploads a new file AND
                # checks the "clear" checkbox), we return a unique marker
                # object that FileField will turn into a ValidationError.
                return FILE_INPUT_CONTRADICTION
            # False signals to clear any existing value, as opposed to just None
            return False
        return upload

    @override
    def value_omitted_from_data(
        self, data: Mapping[str, Any], files: Mapping[str, Any], name: str
    ) -> bool:
        return (
            (name not in data)
            and (name not in files)
            and (self.clear_checkbox_name(name) not in data)
        )


class AdminS3FileInput(S3FileInput):
    """Widget used by the admin page."""

    template_name = "admin/widgets/clearable_file_input.html"
