# The documentation should always reference s3_file_field.S3FileField
# and this cannot change without breaking the migrations of downstream
# projects.
from .fields import S3FileField  # noqa: F401

default_app_config = 's3_file_field.apps.S3FileFieldConfig'

try:
    from importlib import metadata
except ImportError:
    # Running on pre-3.8 Python; use importlib-metadata package
    import importlib_metadata as metadata

assert metadata.version('django-s3-file-field') == '0.0.14'

__version__ = metadata.version('django-s3-file-field')
