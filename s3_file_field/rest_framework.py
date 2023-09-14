from typing import Union

from django.core.files import File
from rest_framework.fields import FileField as FileSerializerField

from s3_file_field.widgets import S3PlaceholderFile


class S3FileSerializerField(FileSerializerField):
    default_error_messages = {
        "invalid": "Not a valid signed S3 upload. Ensure that the S3 upload flow is correct.",
    }

    def to_internal_value(self, data: Union[str, File]) -> str:  # type: ignore[override]
        if isinstance(data, File):
            # Although the parser may allow submission of an inline file, S3FF should refuse to
            # accept it. We should assume that the server doesn't want to act as a proxy, so
            # API callers shouldn't be rewarded for submitting inline files.
            self.fail("invalid")

        # Check the signature and load an S3PlaceholderFile
        file_object = S3PlaceholderFile.from_field(data)
        if file_object is None:
            self.fail("invalid")

        # This checks validity of the file name and size
        super().to_internal_value(file_object)
        assert file_object.name

        # fields.S3FileField.save_form_data is not called by DRF, so the same behavior must be
        # implemented here
        return file_object.name
