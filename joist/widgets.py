import json
from typing import Any, cast, Dict, Iterable, Mapping, Optional

from django.forms import ClearableFileInput, FileField, Widget

from . import settings


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

    template_name = 'joist/s3fileinput.html'

    baseurl: Optional[str] = settings.JOIST_API_BASE_URL

    def __init__(self, attrs=None):
        if attrs is not None and 'baseurl' in attrs:
            self.baseurl = attrs.pop('baseurl')
        super().__init__(attrs)

    def get_context(self, name: str, value: str, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update({'baseurl': self.baseurl or ''})
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

    template_name = 'joist/s3adminfileinput.html'


class S3FormFileField(FileField):
    """form field used by render an model.S3FileField."""

    widget = cast(Widget, S3FileInput)
