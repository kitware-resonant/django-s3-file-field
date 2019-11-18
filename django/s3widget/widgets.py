import json
from typing import Any, cast, Dict, Optional

from django.forms import FileField, FileInput, Widget


class S3FakeFile:
    def __init__(self, info: Dict[str, Any]):
        super().__init__()

        self.name: str = info['id']
        self.original_name: str = info['name']
        self.size: int = info['size']
        self._committed = True

    def __str__(self):
        return self.name


class S3FileInput(FileInput):
    class Media:
        js = ['s3fileinput/s3fileinput.js']

    template_name = 's3fileinput/s3fileinput.html'

    baseurl: Optional[str] = None

    def __init__(self, attrs=None):
        if attrs is not None and 'baseurl' in attrs:
            self.baseurl = attrs.pop('type')
        super().__init__(attrs)

    def get_context(self, name: str, value: str, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update({'baseurl': self.baseurl or ''})
        return context

    def value_from_datadict(self, data, files, name):
        if name in files:
            return files[name]
        if data.get(name):
            # JSON fake file
            return S3FakeFile(json.loads(data[name]))
        upload = files.get(name)
        return upload

    def value_omitted_from_data(self, data, files, name):
        return name not in files and not data.get(name)


class S3AdminFileInput(S3FileInput):
    template_name = 's3fileinput/s3adminfileinput.html'


class S3FormFileField(FileField):
    widget = cast(Widget, S3FileInput)

    def to_python(self, data):
        return super().to_python(data)
