from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.files.storage import default_storage

from s3_file_field.forms import S3PlaceholderFile
from test_app.models import Resource

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.core.files import File

    from s3_file_field.fields import S3FileField


def test_fixtures_stored_file_object(stored_file_object: File[bytes]) -> None:
    """Test the stored_file_object Pytest fixture."""
    assert stored_file_object.name
    assert default_storage.exists(stored_file_object.name)


def test_fixtures_s3ff_field_value_factory(
    s3ff_field_value_factory: Callable[[File[bytes], S3FileField], str],
    stored_file_object: File[bytes],
) -> None:
    """Test the s3ff_field_value_factory Pytest fixture."""
    blob_field = Resource._meta.get_field("blob")
    field_value = s3ff_field_value_factory(stored_file_object, blob_field)

    placeholder_file = S3PlaceholderFile.from_field_value(field_value, blob_field)
    assert placeholder_file is not None
    assert placeholder_file.name == stored_file_object.name
    assert placeholder_file.size == stored_file_object.size
