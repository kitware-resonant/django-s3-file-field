from __future__ import annotations

from typing import IO, TYPE_CHECKING, Any, Self, override

from django.core.files import File
from pydantic import ValidationError as PydanticValidationError

from ._schemas import FieldValue

if TYPE_CHECKING:
    from .fields import S3FileField

    # Django's File is only generic in django-stubs, so it can only be parameterized when type
    # checking; at runtime, a project may not have applied "django_stubs_ext.monkeypatch()"
    _FileBase = File[Any]
else:
    _FileBase = File


class S3PlaceholderFile(_FileBase):
    """
    The stored object named by a signed FieldValue, as a File.

    This is the cleaned or validated value of a submission. It's named and sized from the
    FieldValue, and its content is readable from the S3FileField's storage, so validators and
    clean methods can inspect it.
    """

    name: str
    size: int
    _file: IO[Any] | None

    def __init__(self, field: S3FileField, name: str, size: int) -> None:
        super().__init__(None, name)
        self.storage = field.storage
        # The size is attested by the signed FieldValue, so the storage needn't be queried for it
        self.size = size

    @property
    def file(self) -> IO[Any]:
        # As with a FieldFile, the content is opened from the storage on demand
        if self._file is None:
            self._file = self.storage.open(self.name)
        return self._file

    @file.setter
    def file(self, file: IO[Any] | None) -> None:
        self._file = file

    @override
    def open(self, mode: str | None = None, *args: Any, **kwargs: Any) -> Self:
        # The content is (re)opened from the storage, in the given mode (or the storage's default)
        self.close()
        self._file = (
            self.storage.open(self.name) if mode is None else self.storage.open(self.name, mode)
        )
        return self

    @override
    def close(self) -> None:
        if self._file is not None:
            self._file.close()

    @classmethod
    def from_field_value(cls, field_value: str, field: S3FileField) -> Self | None:
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
        return cls(field, parsed.object_key, parsed.file_size)
