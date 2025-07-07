from __future__ import annotations

from collections.abc import Callable
import functools
import posixpath
from typing import TYPE_CHECKING, Any, Mapping, NoReturn, Protocol

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
        self.name = name
        self.size = size

    def open(
        self,
        mode: str | None = None,
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        closefd: bool = True,
        opener: Callable[[str, int], int] | None = None,
    ) -> NoReturn:
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


class FileInputProtocol(Protocol):
    is_required: bool

    def clear_checkbox_name(self, name: str) -> str: ...  # noqa: E704

    def get_context(
        self, name: str, value, attrs: dict[str, Any]
    ) -> dict[str, Any]:  # noqa: BLK100
        ...

    def value_from_datadict(  # noqa: E704
        self, data: Mapping[str, Any], files: MultiValueDict[str, UploadedFile], name: str
    ) -> Any: ...


class S3FileInputMixin:
    def get_context(self: FileInputProtocol, name, value, attrs) -> dict[str, Any]:
        # The base URL cannot be determined at the time the widget is instantiated
        # (when S3FormFileField.widget_attrs is called).
        # Additionally, because this method is called on a deep copy of the widget each
        # time it's rendered, this assignment to an instance variable is not persisted.
        attrs["data-s3fileinput"] = get_base_url()
        return super().get_context(name, value, attrs)  # type: ignore [safe-super]

    def value_from_datadict(
        self: FileInputProtocol,
        data: Mapping[str, Any],
        files: MultiValueDict[str, UploadedFile],
        name: str,
    ) -> Any:
        if name in data:
            upload = data[name]
            # An empty string indicates the field was not populated, so don't wrap it in a File
            if upload != "":
                upload = S3PlaceholderFile.from_field(upload)
        elif name in files:
            # Files were uploaded, client JS library may not be functioning
            # So, fallback to direct upload
            upload = super().value_from_datadict(data, files, name)  # type: ignore [safe-super]
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
        self: FileInputProtocol, data: Mapping[str, Any], files: Mapping[str, Any], name: str
    ) -> bool:
        return (
            (name not in data)
            and (name not in files)
            and (self.clear_checkbox_name(name) not in data)
        )


class S3FileInput(S3FileInputMixin, ClearableFileInput):
    """Widget to render the S3 File Input."""

    class Media:
        js = ["s3_file_field/widget.js"]
        css = {"all": ["s3_file_field/widget.css"]}


class S3ImageFileInput(S3FileInputMixin, ClearableFileInput):
    """Widget to render the S3 File Input with an image field preview."""

    template_name = "s3_file_field/widgets/image_input.html"

    class Media(S3FileInput.Media):
        js = ["s3_file_field/imagewidget.js"]
        css = {
            "all": [
                "s3_file_field/widget.css",
                "s3_file_field/imagewidget.css",
            ],
        }


class AdminS3FileInput(S3FileInput):
    """Widget used by the admin page."""

    template_name = "admin/widgets/clearable_file_input.html"
