import json
from typing import Any, Dict, Iterable, Mapping

from django.forms import ClearableFileInput

from . import settings
from .configuration import get_base_url, StorageProvider


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
    """widget to render the S3 File Input."""

    class Media:
        js = ['joist/joist.js']

    @property
    def template_name(self):
        if settings._S3FF_STORAGE_PROVIDER == StorageProvider.UNSUPPORTED:
            return 'django/forms/widgets/file.html'
        else:
            return 'joist/s3fileinput.html'

    def get_context(self, name: str, value: str, attrs):
        context = super().get_context(name, value, attrs)
        # TODO: set 'data-...' fields on attrs directly, instead of in template?
        context['widget'].update({'baseurl': get_base_url()})
        return context

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


class S3AdminFileInput(S3FileInput):
    """widget used by the admin page."""

    @property
    def template_name(self):
        if settings._S3FF_STORAGE_PROVIDER == StorageProvider.UNSUPPORTED:
            return 'admin/widgets/clearable_file_input.html'
        else:
            return 'joist/s3adminfileinput.html'
