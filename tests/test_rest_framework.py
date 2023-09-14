import pytest

from test_app.rest import ResourceSerializer


def test_serializer_data_missing():
    serializer = ResourceSerializer(
        data={
            # Omitted field
        }
    )

    assert not serializer.is_valid()
    assert serializer.errors["blob"][0].code == "required"


def test_serializer_data_invalid():
    serializer = ResourceSerializer(
        data={
            # Invalid, this must be a signed field_value
            "blob": "test_key"
        }
    )

    assert not serializer.is_valid()
    assert serializer.errors["blob"][0].code == "invalid"


def test_serializer_is_valid(s3ff_field_value):
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})

    assert serializer.is_valid()


def test_serializer_validated_data(stored_file_object, s3ff_field_value):
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})
    serializer.is_valid(raise_exception=True)

    assert "blob" in serializer.validated_data
    # The field_value fixture is created from the same stored_file_object
    assert serializer.validated_data["blob"] == stored_file_object.name


@pytest.mark.django_db()
def test_serializer_save_create(stored_file_object, s3ff_field_value):
    serializer = ResourceSerializer(data={"blob": s3ff_field_value})

    serializer.is_valid(raise_exception=True)
    resource = serializer.save()

    assert resource.blob.name == stored_file_object.name


@pytest.mark.django_db()
def test_serializer_save_update(resource, stored_file_object, s3ff_field_value):
    serializer = ResourceSerializer(resource, data={"blob": s3ff_field_value})
    # Sanity check
    assert resource.blob.name != stored_file_object.name

    serializer.is_valid(raise_exception=True)
    # save() should modify an existing model instance in-place
    serializer.save()

    assert resource.blob.name == stored_file_object.name
