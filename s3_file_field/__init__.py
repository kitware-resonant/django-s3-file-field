# The documentation should always reference s3_file_field.S3FileField
# and this cannot change without breaking the migrations of downstream
# projects.
from __future__ import annotations

from .fields import S3FileField  # noqa: F401
