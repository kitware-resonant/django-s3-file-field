from django.apps import AppConfig
from rest_framework.serializers import ModelSerializer

from .fields import S3FileField
from .rest_framework import S3FileSerializerField


class S3FileFieldConfig(AppConfig):
    name = "s3_file_field"
    verbose_name = "S3 File Field"

    def ready(self) -> None:
        # import checks to register them
        from . import checks  # noqa: F401

        # Add an entry to the the base ModelSerializer, so S3FF will work out of the box.
        # Otherwise, downstream users would have to explicitly add this mapping (or a direct
        # instantiation of S3FileSerializerField) on every serializer with an S3FileField.
        ModelSerializer.serializer_field_mapping[S3FileField] = S3FileSerializerField
