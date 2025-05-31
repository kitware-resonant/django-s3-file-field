from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from django.core import checks
from django.db.models.fields.files import FileField

from ._multipart import MultipartManager
from ._registry import register_field
from .forms import S3FormFileField
from .widgets import S3PlaceholderFile

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django import forms
    from django.core.checks import CheckMessage
    from django.db import models

logger = logging.getLogger(__name__)


class S3FileField(FileField):
    """
    A django model field that is similar to a file field.

    Except it supports directly uploading the file to S3 via the UI
    """

    description = (
        "A file field which is supports direct uploads to S3 via the "
        "UI and fallsback to uploaded to <randomuuid>/filename."
    )

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("max_length", 2000)
        kwargs.setdefault("upload_to", self.uuid_prefix_filename)
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("max_length") == 2000:
            del kwargs["max_length"]
        if kwargs.get("upload_to") is self.uuid_prefix_filename:
            del kwargs["upload_to"]
        return name, path, args, kwargs

    @property
    def id(self) -> str:
        """Return the unique identifier for this field instance."""
        if not hasattr(self, "model"):
            # TODO: raise a more specific exception
            raise RuntimeError("contribute_to_class has not been called yet on this field.")
        return str(self)

    def contribute_to_class(
        self, cls: type[models.Model], name: str, private_only: bool = False
    ) -> None:
        # This is executed when the Field is formally added to its containing class.
        # As a side effect, self.name is set and self.__str__ becomes usable as a unique
        # identifier for the Field.
        super().contribute_to_class(cls, name, private_only=private_only)
        if cls.__module__ != "__fake__":
            # Django's makemigrations iteratively creates fake model instances.
            # To avoid registration collisions, don't register these.
            register_field(self)

    @staticmethod
    def uuid_prefix_filename(instance: models.Model, filename: str) -> str:
        return f"{uuid4()}/{filename}"

    def formfield(
        self,
        form_class: type[forms.Field] | None = None,
        choices_form_class: type[forms.ChoiceField] | None = None,
        **kwargs: Any,
    ) -> forms.Field | None:
        """
        Return a forms.Field instance for this model field.

        This is an instance of "form_class", with a widget of "widget".
        """
        if MultipartManager.supported_storage(self.storage):
            # Use S3FormFileField as a default, instead of forms.FileField from the superclass
            form_class = S3FormFileField if form_class is None else form_class
            # Allow the form and widget to lookup this field instance later, using its id
            kwargs.setdefault("model_field_id", self.id)
        return super().formfield(
            form_class=form_class, choices_form_class=choices_form_class, **kwargs
        )

    def save_form_data(self, instance: models.Model, data) -> None:
        """Coerce a form field value and assign it to a model instance's field."""
        # The FileField's FileDescriptor behavior provides that when a File object is
        # assigned to the field, the content is considered uncommitted, and is saved.
        # If a string is assigned to the field, it is considered to be the value in the
        # database, and no save occurs, which is desirable here.
        # However, we don't want the S3FileInput or S3FormFileField to emit a string value,
        # since that will break most of the default validation.
        if isinstance(data, S3PlaceholderFile):
            data = data.name
        super().save_form_data(instance, data)

    def check(self, **kwargs: Any) -> list[CheckMessage]:
        return [
            *super().check(**kwargs),
            *self._check_supported_storage_provider(),
        ]

    def _check_supported_storage_provider(self) -> list[checks.CheckMessage]:
        if not MultipartManager.supported_storage(self.storage):
            msg = f"Incompatible storage type used with an {self.__class__.__name__}."
            logger.warning(msg)
            return [checks.Warning(msg, obj=self, id="s3_file_field.W001")]
        return []
