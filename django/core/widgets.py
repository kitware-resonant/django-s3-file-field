from django.forms.widgets import FileInput
from django.conf import settings


class S3FileInput(FileInput):
    class Media:
        if settings.DEBUG:
            js = [
              's3fileinput/s3fileinput.js',
              's3fileinput/aws-sdk-2.566.0.js'
            ]
        else:
            js = [
              's3fileinput/s3fileinput.js',
              's3fileinput/aws-sdk-2.566.0.min.js'
            ]

    template_name = 'widgets/s3fileinput.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'test': 'test'
        })
        return context

    def value_from_datadict(self, data, files, name):
        upload = super().value_from_datadict(data, files, name)
        return upload
