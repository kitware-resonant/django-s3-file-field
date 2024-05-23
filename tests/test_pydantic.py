from pydantic import BaseModel
import pytest

from s3_file_field.pydantic import S3FileFieldValue


class Model(BaseModel):
    blob: S3FileFieldValue


def test_pydantic_serializer_data_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid S3 file field value"):
        Model(blob="invalid_key")


def test_pydantic_serializer_is_valid(s3ff_field_value: str) -> None:
    model = Model(blob=s3ff_field_value)
    assert model.blob.startswith("test_key")
