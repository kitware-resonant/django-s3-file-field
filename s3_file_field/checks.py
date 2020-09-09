import logging
from typing import Iterable, List, Optional

from botocore.exceptions import ConnectionError
from django.apps import AppConfig
from django.core.checks import CheckMessage, Error, register

from ._multipart import MultipartManager
from ._registry import iter_storages

# TODO: this should only add a handler when running the check command
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


E001 = Error('Incompatible storage type used with an S3FileField.', id='s3_file_field.E001')
E002 = Error('Unable to connect to the specified storage bucket.', id='s3_file_field.E002')
E003 = Error('Unable to put objects into the specified storage bucket.', id='s3_file_field.E003')
E004 = Error('Unable to delete objects from the specified storage bucket.', id='s3_file_field.E004')


@register(deploy=True)
def check_supported_storage_provider(
    app_configs: Optional[Iterable[AppConfig]], **kwargs
) -> List[CheckMessage]:
    # TODO: call this from S3FileField.check:
    # https://docs.djangoproject.com/en/3.1/topics/checks/#field-model-manager-and-database-checks
    return (
        []
        if all(MultipartManager.supported_storage(storage) for storage in iter_storages())
        else [E001]
    )


@register()
def test_bucket_access(app_configs: Optional[Iterable[AppConfig]], **kwargs) -> List[CheckMessage]:
    for storage in iter_storages():
        if not MultipartManager.supported_storage(storage):
            continue
        multipart = MultipartManager.from_storage(storage)
        try:
            multipart.test_upload()
        except ConnectionError:
            logger.exception('Failed to connect to storage bucket')
            return [E002]
        except Exception:
            logger.exception('Failed to put an object into the storage bucket.')
            return [E003]
    return []


# TODO: investigate a possible check for CORS misconfigurations
