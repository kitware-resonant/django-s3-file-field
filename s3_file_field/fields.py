import logging
from typing import Any, List, cast
from uuid import uuid4

from django.core import checks
from django.core.checks import CheckMessage
from django.db.models.fields.files import FieldFile, FileField
from django.forms import Field as FormField

from ._multipart import MultipartManager
from ._registry import register_field
from .forms import S3FormFileField
from .widgets import S3FakeFile

logger = logging.getLogger(__name__)


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

    @property
    def id(self) -> str:
        """Return the unique identifier for this field instance."""
        if not hasattr(self, 'model'):
            # TODO: raise a more specific exception
            raise Exception('contribute_to_class has not been called yet on this field.')
        return str(self)

    def contribute_to_class(self, cls, name, **kwargs):
        # This is executed when the Field is formally added to its containing class.
        # As a side effect, self.name is set and self.__str__ becomes usable as a unique
        # identifier for the Field.
        super().contribute_to_class(cls, name, **kwargs)
        if cls.__module__ != '__fake__':
            # Django's makemigrations iteratively creates fake model instances.
            # To avoid registration collisions, don't register these.
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
            # Allow the form and widget to lookup this field instance later, using its id
            kwargs.setdefault('model_field_id', self.id)
        return super().formfield(**kwargs)

    # Ignore type due to: https://github.com/typeddjango/django-stubs/pull/497
    def check(self, **kwargs) -> List[CheckMessage]:  # type: ignore
        return [
            *super().check(**kwargs),
            *self._check_supported_storage_provider(),
        ]

    def _check_supported_storage_provider(self) -> List[checks.CheckMessage]:
        if not MultipartManager.supported_storage(self.storage):
            msg = f'Incompatible storage type used with an {self.__class__.__name__}.'
            logger.warning(msg)
            return [checks.Warning(msg, obj=self, id='s3_file_field.W001')]
        else:
            return []
