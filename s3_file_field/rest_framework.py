from rest_framework.fields import FileField as FileSerializerField

from s3_file_field.widgets import S3PlaceholderFile


class S3FileSerializerField(FileSerializerField):
    default_error_messages = {
        'invalid': 'Not a valid signed S3 upload. Ensure that the S3 upload flow is correct.',
    }

    def to_internal_value(self, data):
        # Check the signature and load an S3PlaceholderFile
        file_object = S3PlaceholderFile.from_field(data)
        if file_object is None:
            self.fail('invalid')

        # This checks validity of the file name and size
        file_object = super().to_internal_value(file_object)

        # fields.S3FileField.save_form_data is not called by DRF, so the same behavior must be
        # implemented here
        internal_value = file_object.name

        return internal_value
