# The documentation should always reference s3_file_field.S3FileField
# and this cannot change without breaking the migrations of downstream
# projects.
from .fields import S3FileField  # noqa: F401

default_app_config = 's3_file_field.apps.S3FileFieldConfig'

version = {}
with open("s3_file_field/version.py") as fp:
    exec(fp.read(), version)

__version__ = version["__version__"]