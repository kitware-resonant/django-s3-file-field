from typing import Any, cast
from uuid import uuid4

from django.contrib.admin.widgets import AdminFileWidget
from django.db.models.fields.files import FieldFile, FileField

from .settings import JOIST_STORAGE_PROVIDER
from .widgets import S3AdminFileInput, S3FakeFile, S3FormFileField


class S3FieldFile(FieldFile):
    """
    Helper class for the S3FileField.

    it wraps the value within a model instance.
    """

    def save(self, name: str, content: Any, save=True):
        if not isinstance(content, S3FakeFile):
            return super().save(name, content, save)

        self.name = content.name
        setattr(self.instance, self.field.name, self.name)
        self._committed = True

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()

    cast(Any, save).alters_data = True


class S3FileField(FileField):
    """
    A django model field that is similar to a file field.

    Except it supports directly uploading the file to S3 via the UI
    """

    attr_class = S3FieldFile
    description = (
        'A file field which is supports direct uploads to S3 via the '
        'UI and fallsback to uploaded to <randomuuid>/filename.'
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 2000)
        kwargs.setdefault('upload_to', self.uuid_prefix_filename)
        super().__init__(*args, **kwargs)

    @staticmethod
    def uuid_prefix_filename(instance: Any, filename: str):
        return f'{uuid4()}/{filename}'

    def formfield(self, **kwargs):
        if JOIST_STORAGE_PROVIDER == 'unknown':
            return super().formfield(**kwargs)

        copy = kwargs.copy()
        if copy.get('widget') == AdminFileWidget:
            # replace for admin
            copy['widget'] = S3AdminFileInput
        copy.setdefault('form_class', S3FormFileField)
        return super().formfield(**copy)
