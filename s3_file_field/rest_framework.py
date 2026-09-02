from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.core.files import File
from rest_framework.fields import FileField as FileSerializerField

from s3_file_field.fields import S3FileField
from s3_file_field.forms import S3PlaceholderFile

if TYPE_CHECKING:
    from rest_framework.serializers import BaseSerializer


class S3FileSerializerField(FileSerializerField):
    default_error_messages = {
        "invalid": "Not a valid signed S3 upload. Ensure that the S3 upload flow is correct.",
    }

    def __init__(self, *, model_field: S3FileField | None = None, **kwargs: Any) -> None:
        self.model_field = model_field
        super().__init__(**kwargs)

    @override
    def bind(self, field_name: str, parent: BaseSerializer[Any]) -> None:
        super().bind(field_name, parent)
        if self.model_field is None:
            # When bound within a ModelSerializer, find the corresponding model field
            try:
                model = parent.Meta.model  # type: ignore[attr-defined]
            except AttributeError:
                model = None
            if model is not None:
                try:
                    model_field = model._meta.get_field(self.source)
                except FieldDoesNotExist:
                    pass
                else:
                    if isinstance(model_field, S3FileField):
                        self.model_field = model_field
        if self.model_field is None and not self.read_only:
            # A read-only field never validates input, so it doesn't need a model_field
            raise ImproperlyConfigured(
                "S3FileSerializerField cannot determine its S3FileField; "
                'pass "model_field" explicitly.'
            )

    @override
    def to_internal_value(self, data: str | File[Any]) -> str:  # type: ignore[override]
        if isinstance(data, File):
            # Although the parser may allow submission of an inline file, S3FF should refuse to
            # accept it. We should assume that the server doesn't want to act as a proxy, so
            # API callers shouldn't be rewarded for submitting inline files.
            self.fail("invalid")

        # bind() ensures model_field is set (or immediately fails) for any writable field attached
        # to a Serializer, but this still could have been instantiated as a stand-alone field.
        if self.model_field is None:
            raise ImproperlyConfigured(
                "S3FileSerializerField cannot determine its S3FileField; "
                'pass "model_field" explicitly.'
            )

        file_object = S3PlaceholderFile.from_field_value(data, self.model_field)
        if file_object is None:
            self.fail("invalid")

        # This checks validity of the file name and size
        super().to_internal_value(file_object)

        # fields.S3FileField.save_form_data is not called by DRF, so the same behavior must be
        # implemented here
        return file_object.name
