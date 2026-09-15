from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NoReturn, override

from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models.fields.files import FieldFile
from django.forms import FileField, Widget
from pydantic import ValidationError as PydanticValidationError

from ._schemas import FieldValue
from .widgets import S3FileInput

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.core.files.uploadedfile import UploadedFile

    from .fields import S3FileField


class S3PlaceholderFile(File[Any]):
    name: str
    size: int

    def __init__(self, name: str, size: int) -> None:
        self.name = name
        self.size = size

    @override
    def open(
        self,
        mode: str | None = None,
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        closefd: bool = True,
        opener: Callable[[str, int], int] | None = None,
    ) -> NoReturn:
        raise NotImplementedError

    @override
    def close(self) -> NoReturn:
        raise NotImplementedError

    @override
    def chunks(self, chunk_size: int | None = None) -> NoReturn:
        raise NotImplementedError

    @override
    def multiple_chunks(self, chunk_size: int | None = None) -> bool:
        # Since it's in memory, we'll never have multiple chunks.
        return False

    @classmethod
    def from_field_value(cls, field_value: str, field: S3FileField) -> S3PlaceholderFile | None:
        try:
            parsed = FieldValue.model_validate(field_value)
        except PydanticValidationError:
            return None
        # Compare field ids, to avoid needlessly depending on instance identities remaining stable
        # (particularly given that the Django form layer frequently deep-copies objects).
        if parsed.field.id != field.id:
            # The FieldValue was minted for a different S3FileField instance; refuse to let it be
            # replayed against this field, which may have a different storage or validation policy.
            return None
        # Since the field is signed, we know the content is structurally valid
        return cls(parsed.object_key, parsed.file_size)


class S3FormFileField(FileField):
    """Form field used by render a model.S3FileField."""

    widget = S3FileInput
    default_error_messages = {
        "invalid": "Not a valid signed S3 upload.",
    }

    def __init__(self, *, model_field: S3FileField, **kwargs: Any) -> None:
        self.model_field = model_field
        super().__init__(**kwargs)

    @override
    def widget_attrs(self, widget: Widget) -> dict[str, str]:
        """
        Return additional HTML attributes for the widget, derived from the model_field.

        This is called when this form field is instantiated.
        """
        attrs = super().widget_attrs(widget)
        attrs.update(
            {
                "field-id": self.model_field.id,
                "max-size": str(self.model_field.effective_max_size),
            }
        )
        return attrs

    @override
    def bound_data[InitialT: FieldFile | None](
        self, data: str | Literal[False] | UploadedFile[Any] | None, initial: InitialT
    ) -> str | Literal[False] | InitialT:
        """Return the value to redisplay for this field when rendering a bound form."""
        if self.disabled:
            # A disabled field ignores submitted data when cleaning, so ignore it here too
            return initial
        if isinstance(data, str) and data:
            # A pending signed FieldValue string is redisplayed (as the widget's "value"), so
            # a completed upload survives a validation error elsewhere on the form.
            return data
        if data is False and initial:
            # A clear of an existing value is redisplayed (as the widget's "cleared" state), so
            # it also survives a validation error elsewhere on the form. Without an existing
            # value, a clear is equivalent to a keep.
            return False
        # Otherwise (a keep), redisplay the initial value.
        return initial

    @override
    def clean(
        self,
        data: str | Literal[False] | UploadedFile[Any] | FieldFile | None,
        initial: FieldFile | None = None,
    ) -> S3PlaceholderFile | FieldFile | Literal[False] | None:
        """
        Validate the submission in light of the existing value, and return the cleaned value.

        This is called by the form, after "S3FileInput.value_from_datadict"; within it, a
        submitted value is converted and validated by "to_python".
        """
        if data is False:
            if not initial:
                # There is no existing value to clear; the widget never submits this
                raise ValidationError(self.error_messages["invalid"], code="invalid")
            if self.required:
                # The widget offers to clear a required field (as with any existing value), so
                # this must be refused explicitly; "FileField.clean" would instead demote the
                # clear to None, which then falls back to the existing value, silently keeping it
                raise ValidationError(self.error_messages["required"], code="required")
        # The superclass is untyped, but it only returns values from "to_python" or "initial"
        cleaned: S3PlaceholderFile | FieldFile | Literal[False] | None = super().clean(
            data, initial
        )
        return cleaned

    @override
    def to_python(self, data: str | File[Any] | None) -> S3PlaceholderFile | FieldFile | None:
        """
        Validate and convert a submitted FieldValue string, independently of any existing value.

        This is called during "clean", for a submitted value.
        """
        # A False (clear) value has already been consumed internally by "FileField.clean",
        # so it never reaches here
        if data in self.empty_values:
            return None
        if isinstance(data, FieldFile):
            # A FieldFile can only be this field's own initial value, cleaned in place of any
            # submitted data when this field is disabled; it never arrives from the wire.
            # It's already stored, so accept it unchanged.
            return data
        if not isinstance(data, str):
            # If this is an inline file upload, it should still be refused. We don't want to reward
            # clients for sending inline files, as it burdens the server (the very thing S3FF
            # seeks to avoid). We'd also need to implement and audit all security measures to the
            # same degree as typical S3FF uploads, which is too much complexity to support.
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        file_object = S3PlaceholderFile.from_field_value(data, self.model_field)
        if file_object is None:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        # Check validity of the file name and size; this returns its argument unchanged
        super().to_python(file_object)
        return file_object
