from typing import cast, Optional

from django.forms import FileField, FileInput, Widget


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
        # File widgets take data from FILES, not POST
        # TODO
        upload = files.get(name)
        return upload

    def value_omitted_from_data(self, data, files, name):
        # TODO
        return name not in files


class S3FormFileField(FileField):
    widget = cast(Widget, S3FileInput)

    def to_python(self, data):
        return super().to_python(data)
