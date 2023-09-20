from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from django.core.files.storage import Storage, default_storage

from s3_file_field.widgets import S3PlaceholderFile

if TYPE_CHECKING:
    from django.core.files import File


def test_fixtures_stored_file_object(stored_file_object: File[bytes]) -> None:
    """Test the stored_file_object Pytest fixture."""
    # Fix https://github.com/typeddjango/django-stubs/issues/1610
    assert isinstance(default_storage, Storage)
    assert stored_file_object.name
    assert default_storage.exists(stored_file_object.name)


def test_fixtures_s3ff_field_value_factory(
    s3ff_field_value_factory: Callable[[File[bytes]], str], stored_file_object: File[bytes]
) -> None:
    """Test the s3ff_field_value_factory Pytest fixture."""
    field_value = s3ff_field_value_factory(stored_file_object)

    placeholder_file = S3PlaceholderFile.from_field(field_value)
    assert placeholder_file is not None
    assert placeholder_file.name == stored_file_object.name
    assert placeholder_file.size == stored_file_object.size


def test_fixtures_s3ff_field_value(s3ff_field_value: str) -> None:
    """Test the s3ff_field_value Pytest fixture."""
    assert S3PlaceholderFile.from_field(s3ff_field_value) is not None
