from __future__ import annotations

import functools
import posixpath
from typing import TYPE_CHECKING, Any, ClassVar, Mapping, NoReturn

from django.core import signing
from django.core.files import File
from django.forms import ClearableFileInput
from django.forms.widgets import FILE_INPUT_CONTRADICTION, CheckboxInput
from django.urls import reverse

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile
    from django.utils.datastructures import MultiValueDict


@functools.lru_cache(maxsize=1)
def get_base_url() -> str:
    prepare_url = reverse("s3_file_field:upload-initialize")
    complete_url = reverse("s3_file_field:upload-complete")
    # Use posixpath to always parse URL paths with forward slashes
    return posixpath.commonpath([prepare_url, complete_url])


class S3PlaceholderFile(File):
    name: str
    size: int

    def __init__(self, name: str, size: int) -> None:
        super().__init__(file=None, name=name)
        self.size = size

    def open(self, mode: str | None = None) -> NoReturn:  # noqa: A003
        raise NotImplementedError

    def close(self) -> NoReturn:
        raise NotImplementedError

    def chunks(self, chunk_size: int | None = None) -> NoReturn:
        raise NotImplementedError

    def multiple_chunks(self, chunk_size: int | None = None) -> bool:
        # Since it's in memory, we'll never have multiple chunks.
        return False

    @classmethod
    def from_field(cls, field_value: str) -> S3PlaceholderFile | None:
        try:
            parsed_field = signing.loads(field_value)
        except signing.BadSignature:
            return None
        # Since the field is signed, we know the content is structurally valid
        return cls(parsed_field["object_key"], parsed_field["file_size"])


class S3FileInput(ClearableFileInput):
    """Widget to render the S3 File Input."""

    class Media:
        js: ClassVar[list[str]] = ["s3_file_field/widget.js"]
        css: ClassVar[dict[str, list[str]]] = {"all": ["s3_file_field/widget.css"]}

    def get_context(self, *args, **kwargs) -> dict[str, Any]:
        # The base URL cannot be determined at the time the widget is instantiated
        # (when S3FormFileField.widget_attrs is called).
        # Additionally, because this method is called on a deep copy of the widget each
        # time it's rendered, this assignment to an instance variable is not persisted.
        self.attrs["data-s3fileinput"] = get_base_url()
        return super().get_context(*args, **kwargs)

    def value_from_datadict(
        self, data: Mapping[str, Any], files: MultiValueDict[str, UploadedFile], name: str
    ) -> Any:
        if name in data:
            upload = data[name]
            # An empty string indicates the field was not populated, so don't wrap it in a File
            if upload != "":
                upload = S3PlaceholderFile.from_field(upload)
        elif name in files:
            # Files were uploaded, client JS library may not be functioning
            # So, fallback to direct upload
            upload = super().value_from_datadict(data, files, name)
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
