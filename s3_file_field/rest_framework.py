from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.core.files import File
from rest_framework.fields import FileField as FileSerializerField
from rest_framework.fields import empty

from s3_file_field.fields import S3FileField
from s3_file_field.files import S3PlaceholderFile
from s3_file_field.widgets import CLEAR_VALUE

if TYPE_CHECKING:
    from rest_framework.serializers import BaseSerializer


class S3FileSerializerField(FileSerializerField):
    """Serializer field used to submit to a model S3FileField."""

    default_error_messages = {
        "invalid": "Not a valid signed S3 upload. Ensure that the S3 upload flow is correct.",
        "null": "This field may not be cleared.",
    }

    def __init__(
        self,
        *,
        model_field: S3FileField | None = None,
        read_only: bool = False,
        required: bool | None = None,
        allow_null: bool | None = None,
        **kwargs: Any,
    ) -> None:
        self._model_field = model_field

        # DRF doesn't support "allow_null = None", but we want to remember whether it was
        # explicitly set
        self._initial_allow_null = allow_null
        if allow_null is not None:
            kwargs["allow_null"] = allow_null

        super().__init__(read_only=read_only, required=required, **kwargs)

    @override
    def bind(self, field_name: str, parent: BaseSerializer[Any]) -> None:
        """
        Attach this field to its serializer, determining its model field if not given explicitly.

        This is called when the serializer's fields are first accessed.
        """
        super().bind(field_name, parent)
        if self._model_field is None:
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
                        self._model_field = model_field
        if not self.read_only:
            # A read-only field never validates input, so it doesn't need a model field;
            # otherwise, ensure it's set (by accessing it) and fail now rather than on the first
            # submission
            model_field = self.model_field
            if self._initial_allow_null is None:
                # If the user doesn't specify "allow_null", derive it from the model, since a
                # ModelSerializer won't set it (unlike properties like "required").
                # This field uses null input to provide a clear operation (see
                # "validate_empty_values" below), so a blank-able model field determines the
                # appropriate value.
                self.allow_null = model_field.blank

    @property
    def model_field(self) -> S3FileField:
        # bind() ensures this is set (or immediately fails) for any writable field attached to a
        # Serializer, but the field could still have been instantiated stand-alone
        if self._model_field is None:
            raise ImproperlyConfigured(
                "S3FileSerializerField cannot determine its S3FileField; "
                'pass "model_field" explicitly.'
            )
        return self._model_field

    @override
    def validate_empty_values(self, data: Any) -> tuple[bool, Any]:
        """
        Translate the wire protocol's empty and clear values to DRF's own conventions.

        This is called with the submitted data, before "to_internal_value" (which is then skipped
        for an empty value).
        """
        if data == "":
            # An empty value is equivalent to an omitted one. The element's "value" is empty when
            # there's nothing to submit, so a client which reads it and sends every field (as a
            # typical form-handling app does) sends an empty value, while one which builds its
            # request from the element's own form data omits the field.
            data = empty
        elif data == CLEAR_VALUE:
            # The clear value is equivalent to null, which a form submission (unlike JSON) can't
            # express. Null is DRF's convention for unsetting a field, permitted by "allow_null";
            # when assigned to the model field, None is stored as an empty name.
            data = None
        return super().validate_empty_values(data)

    @override
    def to_internal_value(self, data: str | File[Any]) -> S3PlaceholderFile:
        """
        Validate and convert a submitted FieldValue string, to a placeholder for its stored object.

        This is called for a non-empty submitted value, after "validate_empty_values".
        """
        if isinstance(data, File):
            # Although the parser may allow submission of an inline file, S3FF should refuse to
            # accept it. We should assume that the server doesn't want to act as a proxy, so
            # API callers shouldn't be rewarded for submitting inline files.
            self.fail("invalid")

        placeholder_file = S3PlaceholderFile.from_field_value(data, self.model_field)
        if placeholder_file is None:
            self.fail("invalid")

        # Check validity of the file name and size; this returns its argument unchanged
        super().to_internal_value(placeholder_file)
        return placeholder_file
