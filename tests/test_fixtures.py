from django.core.files.storage import default_storage

from s3_file_field.widgets import S3PlaceholderFile


def test_fixtures_stored_file_object(stored_file_object):
    """Test the stored_file_object Pytest fixture."""
    assert default_storage.exists(stored_file_object.name)


def test_fixtures_s3ff_field_value_factory(s3ff_field_value_factory, stored_file_object):
    """Test the s3ff_field_value_factory Pytest fixture."""
    field_value = s3ff_field_value_factory(stored_file_object)

    placeholder_file = S3PlaceholderFile.from_field(field_value)
    assert placeholder_file is not None
    assert placeholder_file.name == stored_file_object.name
    assert placeholder_file.size == stored_file_object.size


def test_fixtures_s3ff_field_value(s3ff_field_value):
    """Test the s3ff_field_value Pytest fixture."""
    assert S3PlaceholderFile.from_field(s3ff_field_value) is not None
