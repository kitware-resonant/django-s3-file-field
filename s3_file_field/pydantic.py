from typing import Annotated

from pydantic import PlainValidator

from s3_file_field.fields import S3PlaceholderFile


def _convert_s3ff_value(value: str) -> str:
    file_obj = S3PlaceholderFile.from_field(value)
    if file_obj is None:
        raise ValueError("Invalid S3 file field value")
    return file_obj.name


# This type should be used for S3FF values in Pydantic models.
S3FileFieldValue = Annotated[str, PlainValidator(_convert_s3ff_value)]
