from __future__ import annotations

from typing import TYPE_CHECKING, Iterator
import warnings
from weakref import WeakValueDictionary

from django.core.files.storage import Storage

if TYPE_CHECKING:
    # Avoid circular imports
    from .fields import S3FileField

    FieldsDictType = WeakValueDictionary[str, S3FileField]
    StoragesDictType = WeakValueDictionary[int, Storage]


_fields: FieldsDictType = WeakValueDictionary()
_storages: StoragesDictType = WeakValueDictionary()


def register_field(field: S3FileField) -> None:
    field_id = field.id
    if field_id in _fields and _fields[field_id] is not field:
        # This might be called multiple times, but it should always be consistent
        warnings.warn(
            f"Overwriting existing S3FileField declaration for {field_id}",
            RuntimeWarning,
            # This should attribute to the re-defining class (instead of S3FF or Django internals),
            # but it was determined empirically and could break if Django is restructured.
            stacklevel=5,
        )
    _fields[field_id] = field

    storage = field.storage
    storage_label = id(storage)
    _storages[storage_label] = storage


def get_field(field_id: str) -> S3FileField:
    """Get an S3FileFields by its __str__."""
    return _fields[field_id]


def iter_fields() -> Iterator[S3FileField]:
    """Iterate over the S3FileFields in use."""
    return _fields.values()


def iter_storages() -> Iterator[Storage]:
    """Iterate over the unique Storage instances used by S3FileFields."""
    return _storages.values()
