from typing import cast

from django.conf import settings
from django.forms import FileField, FileInput, Widget


class S3FileInput(FileInput):
    class Media:
        if settings.DEBUG:
            js = ['s3fileinput/s3fileinput.js', 's3fileinput/aws-sdk-2.566.0.js']
        else:
            js = ['s3fileinput/s3fileinput.js', 's3fileinput/aws-sdk-2.566.0.min.js']

    template_name = 's3fileinput/s3fileinput.html'

    def get_context(self, name: str, value: str, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update({'test': 'test'})
        return context

    def value_from_datadict(self, data, files, name):
        upload = super().value_from_datadict(data, files, name)
        return upload


class S3FormFileField(FileField):
    widget = cast(Widget, S3FileInput)
