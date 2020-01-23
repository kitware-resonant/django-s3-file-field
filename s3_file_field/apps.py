from django.apps import AppConfig


class S3FileFieldConfig(AppConfig):
    name = 's3_file_field'
    verbose_name = 'S3 File Field'

    def ready(self):
        # import checks to register them
        from . import checks  # noqa: F401
