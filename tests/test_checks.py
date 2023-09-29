from s3_file_field import checks


def test_checks_test_bucket_access_success() -> None:
    assert checks.test_bucket_access(None) == []
