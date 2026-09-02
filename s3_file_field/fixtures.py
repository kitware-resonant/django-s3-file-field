# This module shouldn't be imported explicitly, as it will be loaded by pytest via entry point.
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import pytest

from ._schemas import FieldValue

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from django.core.files import File

    from .fields import S3FileField


@pytest.fixture
def stored_file_object() -> Generator[File[bytes]]:
    """Return a File object, already saved directly into the default Storage."""
    # Ensure the name is always randomized, even if the key doesn't exist already
    key = default_storage.get_alternative_name("test_key", "")
    # In theory, Storage.save can change the key, though this shouldn't happen with a randomized key
    key = default_storage.save(key, ContentFile(b"test content"))
    # Storage.open will return a File object, which knows its size and can access its content
    with default_storage.open(key) as file_object:
        yield file_object
    default_storage.delete(key)


@pytest.fixture
def s3ff_field_value_factory() -> Callable[[File[bytes], S3FileField], str]:
    """Return a function to produce a valid field_value from a File object."""

    def s3ff_field_value_factory(file_object: File[bytes], field: S3FileField) -> str:
        field_value = FieldValue.model_construct(
            field=field,
            object_key=file_object.name,
            file_size=file_object.size,
        ).model_dump()
        # SignedModel serializes itself to a str, but type stubs cannot express this
        return cast("str", field_value)

    return s3ff_field_value_factory
