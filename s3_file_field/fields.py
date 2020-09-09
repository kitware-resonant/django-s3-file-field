from typing import Any, cast
from uuid import uuid4

from django.db.models.fields.files import FieldFile, FileField
from django.forms import Field as FormField

from ._multipart import MultipartManager
from ._registry import register_field
from .forms import S3FormFileField
from .widgets import S3FakeFile


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

    def contribute_to_class(self, cls, name, **kwargs):
        # This is executed when the Field is formally added to its containing class.
        # As a side effect, self.name is set and self.__str__ becomes usable as a unique
        # identifier for the Field.
        super().contribute_to_class(cls, name, **kwargs)
        register_field(self)

    @staticmethod
    def uuid_prefix_filename(instance: Any, filename: str):
        return f'{uuid4()}/{filename}'

    def formfield(self, **kwargs) -> FormField:
        """
        Return a forms.Field instance for this model field.

        This is an instance of "form_class", with a widget of "widget".
        """
        if MultipartManager.supported_storage(self.storage):
            # Use S3FormFileField as a default, instead of forms.FileField from the superclass
            kwargs.setdefault('form_class', S3FormFileField)
        return super().formfield(**kwargs)
