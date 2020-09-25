from s3_file_field import _registry
from s3_file_field.fields import S3FileField


def test_registry_get_field(s3ff_field: S3FileField):
    assert _registry.get_field(s3ff_field.id) is s3ff_field


def test_registry_iter_fields(s3ff_field: S3FileField):
    fields = list(_registry.iter_fields())

    assert len(fields) == 3
    assert any(field is s3ff_field for field in fields)


def test_registry_iter_storages(s3ff_field: S3FileField):
    storages = list(_registry.iter_storages())

    assert len(storages) == 3
    assert any(storage is s3ff_field.storage for storage in storages)
