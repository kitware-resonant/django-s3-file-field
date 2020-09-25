import pytest

from s3_file_field.fields import S3FileField


def test_field_id(s3ff_field: S3FileField):
    assert s3ff_field.id.startswith('s3ff_test.Resource.blob_')


def test_field_id_premature():
    s3ff_field = S3FileField()
    with pytest.raises(Exception, match=r'contribute_to_class'):
        s3ff_field.id
