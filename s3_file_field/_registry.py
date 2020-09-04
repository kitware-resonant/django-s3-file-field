from typing import TYPE_CHECKING, Iterator
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    # Avoid circular imports
    from .fields import S3FileField

    FieldsType = WeakValueDictionary[str, 'S3FileField']


_fields: 'FieldsType' = WeakValueDictionary()


def register_field(field: 'S3FileField') -> None:
    field_label = str(field)
    if field_label in _fields:
        raise Exception(f'Duplicate S3FileField declaration: {field_label}')
    _fields[field_label] = field


def get_field(field_name: str) -> 'S3FileField':
    return _fields[field_name]


def iter_fields() -> Iterator['S3FileField']:
    return _fields.values()
