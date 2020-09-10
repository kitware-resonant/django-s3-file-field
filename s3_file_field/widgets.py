import functools
import json
import posixpath
from typing import Any, Dict, Iterable, Mapping

from django.forms import ClearableFileInput
from django.urls import reverse


@functools.lru_cache(maxsize=1)
def get_base_url() -> str:
    prepare_url = reverse('s3_file_field:upload-initialize')
    finalize_url = reverse('s3_file_field:upload-finalize')
    # Use posixpath to always parse URL paths with forward slashes
    return posixpath.commonpath([prepare_url, finalize_url])


class S3FakeFile:
    """
    helper object to act similar to an UploadedFile.

    But without the data since they already have been uploaded.
    """

    def __init__(self, info: Mapping[str, Any]):
        super().__init__()

        self.name: str = info['id']
        self.original_name: str = info['name']
        self.size: int = info['size']
        self.signature: str = info['signature']
        self._committed = True

    def __str__(self):
        return self.name

    def bool(self):
        return bool(self.name)

    def len(self):
        return self.size


class S3FileInput(ClearableFileInput):
    """Widget to render the S3 File Input."""

    class Media:
        js = ['joist/joist.js']

    def get_context(self, *args, **kwargs):
        # The base URL cannot be determined at the time the widget is instantiated
        # (when S3FormFileField.widget_attrs is called).
        # Additionally, because this method is called on a deep copy of the widget each
        # time it's rendered, this assignment to an instance variable is not persisted.
        self.attrs['data-s3fileinput'] = get_base_url()
        return super().get_context(*args, **kwargs)

    def value_from_datadict(
        self, data: Dict[str, Any], files: Mapping[str, Iterable[Any]], name: str
    ):
        if name not in files and data.get(name):
            # JSON fake file
            return S3FakeFile(json.loads(data[name]))
        return super().value_from_datadict(data, files, name)

    def value_omitted_from_data(self, data: Mapping[str, Any], files: Mapping[str, Any], name: str):
        return (
            name not in files and not data.get(name) and self.clear_checkbox_name(name) not in data
        )


class AdminS3FileInput(S3FileInput):
    """Widget used by the admin page."""

    template_name = 'admin/widgets/clearable_file_input.html'
