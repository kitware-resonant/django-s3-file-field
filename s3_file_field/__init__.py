import django

# The documentation should always reference s3_file_field.S3FileField
# and this cannot change without breaking the migrations of downstream
# projects.
from .fields import S3FileField

if django.VERSION < (3, 2):
    default_app_config = 's3_file_field.apps.S3FileFieldConfig'

__all__ = ['S3FileField']
