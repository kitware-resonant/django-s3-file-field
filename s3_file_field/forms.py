from __future__ import annotations

from typing import TYPE_CHECKING, Any, NoReturn, override

from django.contrib.admin.widgets import AdminFileWidget
from django.core.exceptions import ValidationError
from django.core.files import File
from django.forms import FileField, Widget
from pydantic import ValidationError as PydanticValidationError

from ._schemas import FieldValue
from .widgets import AdminS3FileInput, S3FileInput

if TYPE_CHECKING:
    from collections.abc import Callable

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

    def __init__(
        self,
        *,
        model_field: S3FileField,
        widget: type[Widget] | Widget | None = None,
        **kwargs: Any,
    ) -> None:
        self.model_field = model_field

        # For form fields created under django.contrib.admin.options.BaseModelAdmin, any form
        # field representing a model.FileField subclass will request a
        # django.contrib.admin.widgets.AdminFileWidget as a 'widget' parameter override
        # Custom subclasses of BaseModelAdmin can use formfield_overrides to change
        # the default widget for their forms, but this is burdensome
        # So, instead change any requests for an AdminFileWidget to a S3AdminFileInput
        if widget:
            if isinstance(widget, type):
                # widget is a type
                if issubclass(widget, AdminFileWidget):
                    widget = AdminS3FileInput
            else:  # noqa: PLR5501
                # widget is an instance
                if isinstance(widget, AdminFileWidget):
                    # We can't easily re-instantiate the Widget, since we need its initial
                    # parameters, so attempt to rebuild the constructor parameters
                    widget = AdminS3FileInput(attrs={"type": widget.input_type, **widget.attrs})

        super().__init__(widget=widget, **kwargs)

    @override
    def widget_attrs(self, widget: Widget) -> dict[str, str]:
        attrs = super().widget_attrs(widget)
        attrs.update(
            {
                "data-field-id": self.model_field.id,
                "data-s3fileinput": "",
            }
        )
        # 'data-s3fileinput' cannot be determined at this point, during app startup.
        # It will be added at render-time by "S3FileInput.get_context".
        return attrs

    @override
    def to_python(self, data: Any) -> Any:
        if data in self.empty_values:
            return None
        if not isinstance(data, str):
            # If this is an inline file upload, it should still be refused. We don't want to reward
            # clients for sending inline files, as it burdens the server (the very thing S3FF
            # seeks to avoid). We'd also need to implement and audit all security measures to the
            # same degree as typical S3FF uploads, which is too much complexity to support.
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        file_object = S3PlaceholderFile.from_field_value(data, self.model_field)
        if file_object is None:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        # Check validity of the file name and size
        return super().to_python(file_object)
